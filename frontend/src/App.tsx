import { useState, useEffect, useRef } from "react";
import UploadZone from "./components/UploadZone";
import StatusBadge from "./components/StatusBadge";

type AppStatus = "idle" | "uploading" | "queued" | "processing" | "done" | "failed";

export default function App() {
  const [status, setStatus] = useState<AppStatus>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string>("");
  const [error, setError] = useState<string>("");
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
        if (data.status === "done" || data.status === "failed") {
          setStatus(data.status);
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
    setStatus("uploading");
    setError("");

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/translate", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJobId(data.job_id);
      setStatus("queued");
    } catch (e: unknown) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : "Upload failed.");
    }
  };

  const handleDownload = () => {
    window.location.href = `/download/${jobId}`;
  };

  const handleReset = () => {
    stopPolling();
    setStatus("idle");
    setJobId(null);
    setFilename("");
    setError("");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-xl p-10 flex flex-col gap-8">

        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">DocTranslate</h1>
          <p className="text-gray-500 mt-1 text-sm">English → French · .docx</p>
        </div>

        {/* Upload zone — only show when idle */}
        {status === "idle" && (
          <UploadZone onFileSelect={handleFileSelect} disabled={false} />
        )}

        {/* Status area */}
        {status !== "idle" && (
          <div className="flex flex-col items-center gap-6">
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm text-gray-500 font-medium">{filename}</p>
              <StatusBadge status={status} />
            </div>

            {status === "processing" && (
              <p className="text-xs text-gray-400 text-center">
                Translation in progress — this may take a minute for longer documents.
              </p>
            )}

            {status === "done" && (
              <button
                onClick={handleDownload}
                className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-colors duration-200"
              >
                Download Translated Document
              </button>
            )}

            {status === "failed" && (
              <p className="text-sm text-red-500 text-center">{error || "Something went wrong."}</p>
            )}

            {(status === "done" || status === "failed") && (
              <button
                onClick={handleReset}
                className="text-sm text-gray-400 hover:text-gray-600 underline transition-colors"
              >
                Translate another document
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
