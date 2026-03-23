import uuid
import os
import sys
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from docx2pdf import convert

# Allow importing translation_engine from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_engine import run_pipeline, run_pipeline_pptx, run_pipeline_pdf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (replaced by RDS on AWS)
jobs: dict[str, dict] = {}

UPLOAD_DIR = "/tmp/translation_jobs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def run_translation_job(job_id: str, input_path: str, output_path: str):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0

        def on_progress(done: int, total: int):
            jobs[job_id]["progress"] = int((done / total) * 100)

        filetype = jobs[job_id]["filetype"]
        if filetype == "pptx":
            run_pipeline_pptx(input_path, output_path, progress_callback=on_progress)
        elif filetype == "pdf":
            run_pipeline_pdf(input_path, output_path, progress_callback=on_progress)
        else:
            run_pipeline(input_path, output_path, progress_callback=on_progress)

        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "done"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/translate")
async def translate(file: UploadFile, background_tasks: BackgroundTasks):
    if not file.filename or not file.filename.endswith((".docx", ".pptx", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .docx, .pptx, and .pdf files are supported")

    if file.filename.endswith(".pptx"):
        filetype = "pptx"
    elif file.filename.endswith(".pdf"):
        filetype = "pdf"
    else:
        filetype = "docx"
    job_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input.{filetype}")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output.{filetype}")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    jobs[job_id] = {"status": "queued", "filename": file.filename, "filetype": filetype}
    background_tasks.add_task(run_translation_job, job_id, input_path, output_path)

    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job["status"], "filename": job.get("filename"), "progress": job.get("progress", 0)}


@app.get("/download/{job_id}")
def download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Translation not ready")

    filetype = job.get("filetype", "docx")
    ext = f".{filetype}"
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    }
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output{ext}")
    original_name = job.get("filename", f"document{ext}").replace(ext, "")
    return FileResponse(
        output_path,
        media_type=media_types[filetype],
        filename=f"{original_name}_translated{ext}",
    )


@app.get("/preview/{job_id}/{doc_type}")
def preview_pdf(job_id: str, doc_type: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if doc_type not in ("original", "translated"):
        raise HTTPException(status_code=400, detail="doc_type must be 'original' or 'translated'")
    if doc_type == "translated" and job["status"] != "done":
        raise HTTPException(status_code=400, detail="Translation not ready")
    filetype = job.get("filetype", "docx")

    if filetype == "pptx":
        raise HTTPException(status_code=501, detail="PDF preview not available for .pptx files")

    if filetype == "pdf":
        # Input and output are already PDFs — serve directly
        suffix = "input" if doc_type == "original" else "output"
        pdf_path = os.path.join(UPLOAD_DIR, f"{job_id}_{suffix}.pdf")
        return FileResponse(pdf_path, media_type="application/pdf")

    # DOCX — convert to PDF on demand
    docx_path = os.path.join(UPLOAD_DIR, f"{job_id}_{'input' if doc_type == 'original' else 'output'}.docx")
    pdf_path = os.path.join(UPLOAD_DIR, f"{job_id}_{doc_type}.pdf")

    if not os.path.exists(pdf_path):
        convert(docx_path, pdf_path)

    return FileResponse(pdf_path, media_type="application/pdf")
