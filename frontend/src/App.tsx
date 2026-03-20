import { useState, useEffect, useRef } from "react";
import UploadZone from "./components/UploadZone";
import StatusBadge from "./components/StatusBadge";
import SplitPane from "./components/SplitPane";
import DocumentViewer from "./components/DocumentViewer";
import ProgressBar from "./components/ProgressBar";

type AppStatus = "idle" | "uploading" | "queued" | "processing" | "done" | "failed";

export default function App() {
  const [status, setStatus] = useState<AppStatus>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [originalPdfUrl, setOriginalPdfUrl] = useState<string | null>(null);
  const [translatedPdfUrl, setTranslatedPdfUrl] = useState<string | null>(null);
  const [filename, setFilename] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    if (!jobId || status === "done" || status === "failed") return;

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/status/${jobId}`);
        const data = await res.json();
        if (typeof data.progress === "number") setProgress(data.progress);
        if (data.status === "done") {
          if (!filename.endsWith(".pptx")) {
            setTranslatedPdfUrl(`/preview/${jobId}/translated`);
          }
          setStatus("done");
          stopPolling();
        } else if (data.status === "failed") {
          setStatus("failed");
          stopPolling();
        } else {
          setStatus(data.status);
        }
      } catch {
        setStatus("failed");
        setError("Lost connection to server.");
        stopPolling();
      }
    }, 2000);

    return stopPolling;
  }, [jobId, status]);

  const handleFileSelect = async (file: File) => {
    setFilename(file.name);
    setOriginalPdfUrl(null);
    setTranslatedPdfUrl(null);
    setStatus("uploading");
    setError("");

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/translate", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJobId(data.job_id);
      if (!file.name.endsWith(".pptx")) {
        setOriginalPdfUrl(`/preview/${data.job_id}/original`);
      }
      setStatus("queued");
    } catch (e: unknown) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : "Upload failed.");
    }
  };

  const handleDownload = () => {
    if (!jobId) return;
    const ext = filename.endsWith(".pptx") ? ".pptx" : ".docx";
    const a = document.createElement("a");
    a.href = `/download/${jobId}`;
    a.download = filename.replace(ext, `_translated${ext}`);
    a.click();
  };

  const handleReset = () => {
    stopPolling();
    setStatus("idle");
    setJobId(null);
    setOriginalPdfUrl(null);
    setTranslatedPdfUrl(null);
    setFilename("");
    setError("");
    setProgress(0);
  };

  // ── Split-pane view (after file selected) ──────────────────────────
  if (status !== "idle") {
    return (
      <div className="flex flex-col h-screen bg-white">
        {/* Top bar */}
        <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-3">
            <span className="font-bold text-gray-900 text-lg">DocTranslate</span>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500 truncate max-w-xs">{filename}</span>
          </div>
          <div className="flex items-center gap-4">
            <StatusBadge status={status} />
            {status === "done" && (
              <button
                onClick={handleDownload}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Download
              </button>
            )}
            <button
              onClick={handleReset}
              className="px-4 py-1.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 hover:border-gray-300 rounded-lg transition-colors"
            >
              New document
            </button>
          </div>
        </div>

        {/* Progress bar — visible during processing */}
        {status === "processing" && (
          <div className="shrink-0 px-6 py-2 border-b border-gray-100 bg-white">
            <ProgressBar progress={progress} />
          </div>
        )}

        {/* Split pane */}
        <div className="flex-1 overflow-hidden">
          <SplitPane
            left={
              <DocumentViewer
                pdfUrl={originalPdfUrl}
                label="Original (English)"
                placeholder={filename.endsWith(".pptx") ? "PDF preview unavailable for .pptx — download to view" : undefined}
              />
            }
            right={
              <DocumentViewer
                pdfUrl={translatedPdfUrl}
                label="Translation (French)"
                placeholder={
                  status === "failed"
                    ? (error || "Translation failed.")
                    : filename.endsWith(".pptx")
                    ? "PDF preview unavailable for .pptx — download when ready"
                    : "Translation in progress…"
                }
              />
            }
          />
        </div>
      </div>
    );
  }

  // ── Upload view ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-6">
      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-xl p-10 flex flex-col gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">DocTranslate</h1>
          <p className="text-gray-500 mt-1 text-sm">English → French · .docx / .pptx</p>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <UploadZone onFileSelect={handleFileSelect} disabled={false} fileType="docx" />
          <UploadZone onFileSelect={handleFileSelect} disabled={false} fileType="pptx" />
        </div>
      </div>
    </div>
  );
}
