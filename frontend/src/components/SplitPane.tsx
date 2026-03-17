import { useCallback, useEffect, useRef, useState } from "react";

interface Props {
  left: React.ReactNode;
  right: React.ReactNode;
}

export default function SplitPane({ left, right }: Props) {
  const [splitPct, setSplitPct] = useState(50);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = () => {
    dragging.current = true;
  };

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    setSplitPct(Math.min(Math.max(pct, 20), 80));
  }, []);

  const onMouseUp = () => {
    dragging.current = false;
  };

  useEffect(() => {
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMouseMove]);

  return (
    <div ref={containerRef} className="flex h-full w-full overflow-hidden select-none">
      {/* Left pane */}
      <div style={{ width: `${splitPct}%` }} className="h-full overflow-hidden border-r border-gray-200">
        {left}
      </div>

      {/* Draggable divider */}
      <div
        onMouseDown={onMouseDown}
        className="relative z-10 flex items-center justify-center w-2 shrink-0 bg-gray-200 hover:bg-blue-400 cursor-col-resize transition-colors duration-150 group"
      >
        <div className="flex flex-col gap-1">
          <div className="w-0.5 h-4 bg-gray-400 group-hover:bg-white rounded-full" />
          <div className="w-0.5 h-4 bg-gray-400 group-hover:bg-white rounded-full" />
          <div className="w-0.5 h-4 bg-gray-400 group-hover:bg-white rounded-full" />
        </div>
      </div>

      {/* Right pane */}
      <div style={{ width: `${100 - splitPct}%` }} className="h-full overflow-hidden">
        {right}
      </div>
    </div>
  );
}
