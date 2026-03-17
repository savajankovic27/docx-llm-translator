import uuid
import os
import sys
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Allow importing translation_engine from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_engine import run_pipeline

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
        run_pipeline(input_path, output_path)
        jobs[job_id]["status"] = "done"
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/translate")
async def translate(file: UploadFile, background_tasks: BackgroundTasks):
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    job_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input.docx")
    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output.docx")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    jobs[job_id] = {"status": "queued", "filename": file.filename}
    background_tasks.add_task(run_translation_job, job_id, input_path, output_path)

    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job["status"], "filename": job.get("filename")}


@app.get("/download/{job_id}")
def download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Translation not ready")

    output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output.docx")
    original_name = job.get("filename", "document.docx").replace(".docx", "")
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{original_name}_translated.docx",
    )
