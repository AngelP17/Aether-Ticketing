export const PRIORITIES = ["Critical", "High", "Medium", "Low"] as const;

export type Priority = (typeof PRIORITIES)[number];

export const PRIORITY_TONE: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  Critical: {
    border: "border-rose-500/30",
    bg: "bg-rose-500/10",
    text: "text-rose-200",
    dot: "bg-rose-400",
  },
  High: {
    border: "border-orange-500/30",
    bg: "bg-orange-500/10",
    text: "text-orange-200",
    dot: "bg-orange-400",
  },
  Medium: {
    border: "border-amber-500/30",
    bg: "bg-amber-500/10",
    text: "text-amber-200",
    dot: "bg-amber-400",
  },
  Low: {
    border: "border-zinc-700/60",
    bg: "bg-zinc-800/60",
    text: "text-zinc-300",
    dot: "bg-zinc-500",
  },
};

export function priorityTone(priority: string) {
  return PRIORITY_TONE[priority] ?? PRIORITY_TONE.Low;
}

export const STATUS_TONE: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  Open: {
    border: "border-amber-500/30",
    bg: "bg-amber-500/10",
    text: "text-amber-200",
    dot: "bg-amber-400",
  },
  "In Progress": {
    border: "border-cyan-500/30",
    bg: "bg-cyan-500/10",
    text: "text-cyan-200",
    dot: "bg-cyan-400",
  },
  "Waiting for Info": {
    border: "border-rose-500/30",
    bg: "bg-rose-500/10",
    text: "text-rose-200",
    dot: "bg-rose-400",
  },
  "Waiting Info": {
    border: "border-rose-500/30",
    bg: "bg-rose-500/10",
    text: "text-rose-200",
    dot: "bg-rose-400",
  },
  Resolved: {
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/10",
    text: "text-emerald-200",
    dot: "bg-emerald-400",
  },
  Closed: {
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/10",
    text: "text-emerald-200",
    dot: "bg-emerald-400",
  },
};

export function statusTone(status: string) {
  return STATUS_TONE[status] ?? {
    border: "border-zinc-700/60",
    bg: "bg-zinc-800/60",
    text: "text-zinc-300",
    dot: "bg-zinc-500",
  };
}
