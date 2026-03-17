import { useEffect, useState } from "react";
import mammoth from "mammoth";

interface Props {
  file: File | Blob | null;
  label: string;
  placeholder?: string;
}

export default function DocumentViewer({ file, label, placeholder }: Props) {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!file) {
      setHtml("");
      return;
    }
    setLoading(true);
    file.arrayBuffer().then((buf) => {
      mammoth
        .convertToHtml({ arrayBuffer: buf })
        .then((result) => setHtml(result.value))
        .finally(() => setLoading(false));
    });
  }, [file]);

  return (
    <div className="flex flex-col h-full">
      {/* Pane header */}
      <div className="shrink-0 px-4 py-2 bg-gray-100 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-widest">
        {label}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading && (
          <div className="flex items-center justify-center h-full text-gray-400 gap-2">
            <span className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
            Rendering document...
          </div>
        )}

        {!loading && !html && (
          <div className="flex items-center justify-center h-full text-gray-300 text-sm text-center px-8">
            {placeholder ?? "No document loaded"}
          </div>
        )}

        {!loading && html && (
          <div
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )}
      </div>
    </div>
  );
}
