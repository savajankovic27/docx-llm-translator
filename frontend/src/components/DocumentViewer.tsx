interface Props {
  pdfUrl: string | null;
  label: string;
  placeholder?: string;
}

export default function DocumentViewer({ pdfUrl, label, placeholder }: Props) {
  return (
    <div className="flex flex-col h-full">
      {/* Pane header */}
      <div className="shrink-0 px-4 py-2 bg-gray-100 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-widest">
        {label}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {!pdfUrl ? (
          <div className="flex items-center justify-center h-full text-gray-300 text-sm text-center px-8">
            {placeholder ?? "No document loaded"}
          </div>
        ) : (
          <iframe
            src={pdfUrl}
            className="w-full h-full border-0"
            title={label}
          />
        )}
      </div>
    </div>
  );
}
