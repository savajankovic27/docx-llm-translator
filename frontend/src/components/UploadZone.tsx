import { useRef, useState } from "react";

interface Props {
  onFileSelect: (file: File) => void;
  disabled: boolean;
  fileType: "docx" | "pptx";
}

const CONFIG = {
  docx: {
    accept: ".docx",
    icon: "📄",
    label: "Word Document",
    ext: ".docx",
  },
  pptx: {
    accept: ".pptx",
    icon: "📊",
    label: "PowerPoint Presentation",
    ext: ".pptx",
  },
};

export default function UploadZone({ onFileSelect, disabled, fileType }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const { accept, icon, label, ext } = CONFIG[fileType];

  const handleFile = (file: File) => {
    if (!file.name.endsWith(ext)) {
      alert(`This box only accepts ${ext} files.`);
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
        border-2 border-dashed rounded-2xl p-12 cursor-pointer
        transition-colors duration-200
        ${dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <div className="text-5xl">{icon}</div>
      <p className="text-base font-semibold text-gray-700">{label}</p>
      <p className="text-sm text-blue-600 font-medium">{ext}</p>
      <p className="text-sm text-gray-400">Drop here or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
    </div>
  );
}
