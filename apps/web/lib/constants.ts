import { TaskStatus } from "@/types";

export const COLUMN_ORDER: TaskStatus[] = ["backlog", "plan", "in_progress", "testing", "done"];

export const COLUMN_LABELS: Record<TaskStatus, string> = {
  backlog: "Backlog",
  plan: "Plan",
  in_progress: "In Progress",
  testing: "Testing",
  done: "Done",
};

export const STATUS_COLORS: Record<TaskStatus, string> = {
  backlog: "bg-slate-100 text-slate-700",
  plan: "bg-purple-100 text-purple-700",
  in_progress: "bg-blue-100 text-blue-700",
  testing: "bg-amber-100 text-amber-700",
  done: "bg-green-100 text-green-700",
};

// Top border accent per column
export const COLUMN_MARKER_COLORS: Record<TaskStatus, string> = {
  backlog: "border-t-slate-300",
  plan: "border-t-purple-400",
  in_progress: "border-t-blue-500",
  testing: "border-t-amber-400",
  done: "border-t-green-500",
};

// Dot fill color for stage track strip
export const STAGE_DOT_COLORS: Record<TaskStatus, string> = {
  backlog: "bg-slate-400",
  plan: "bg-purple-400",
  in_progress: "bg-blue-500",
  testing: "bg-amber-400",
  done: "bg-green-500",
};

// Numeric index for stage track (0–4)
export const STAGE_INDEX: Record<TaskStatus, number> = {
  backlog: 0,
  plan: 1,
  in_progress: 2,
  testing: 3,
  done: 4,
};

export const EXECUTION_STATUS_COLORS: Record<string, string> = {
  pending: "bg-slate-400",
  running: "bg-blue-500 animate-pulse",
  completed: "bg-green-500",
  failed: "bg-red-500",
  stopped: "bg-amber-500",
};

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
