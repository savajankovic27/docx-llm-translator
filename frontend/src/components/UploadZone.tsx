import { useRef, useState } from "react";

interface Props {
  onFileSelect: (file: File) => void;
  disabled: boolean;
}

export default function UploadZone({ onFileSelect, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = (file: File) => {
    if (!file.name.endsWith(".docx") && !file.name.endsWith(".pptx")) {
      alert("Only .docx and .pptx files are supported.");
      return;
    }
    onFileSelect(file);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`
        flex flex-col items-center justify-center gap-3
        border-2 border-dashed rounded-2xl p-16 cursor-pointer
        transition-colors duration-200
        ${dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <div className="text-5xl">📄</div>
      <p className="text-lg font-medium text-gray-700">
        Drop your <span className="text-blue-600">.docx</span> or <span className="text-blue-600">.pptx</span> file here
      </p>
      <p className="text-sm text-gray-400">or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept=".docx,.pptx"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
    </div>
  );
}
