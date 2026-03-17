type Status = "uploading" | "queued" | "processing" | "done" | "failed";

const config: Record<Status, { label: string; classes: string; icon: string }> = {
  uploading:  { label: "Uploading...",   icon: "⬆️",  classes: "bg-blue-100 text-blue-700" },
  queued:     { label: "Queued",         icon: "🕐",  classes: "bg-yellow-100 text-yellow-700" },
  processing: { label: "Translating...", icon: "⚙️",  classes: "bg-purple-100 text-purple-700" },
  done:       { label: "Complete",       icon: "✅",  classes: "bg-green-100 text-green-700" },
  failed:     { label: "Failed",         icon: "❌",  classes: "bg-red-100 text-red-700" },
};

export default function StatusBadge({ status }: { status: Status }) {
  const { label, icon, classes } = config[status];
  return (
    <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${classes}`}>
      <span>{icon}</span>
      {label}
      {(status === "queued" || status === "processing") && (
        <span className="ml-1 inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
    </span>
  );
}
