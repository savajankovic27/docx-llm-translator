interface Props {
  progress: number; // 0–100
}

export default function ProgressBar({ progress }: Props) {
  return (
    <div className="w-full flex flex-col gap-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>Translating…</span>
        <span className="font-medium">{progress}%</span>
      </div>
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
