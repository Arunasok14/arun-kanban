"use client";

import { useEffect, useRef } from "react";
import { LogEntry } from "@/types";

interface ExecutionLogViewerProps {
  logs: LogEntry[];
  connStatus: string;
  execStatus: string | null;
}

const LEVEL_COLORS: Record<string, string> = {
  stdout: "text-slate-200",
  stderr: "text-red-400",
  system: "text-blue-400",
  tool_use: "text-amber-400",
};

function formatContent(level: string, content: string): string {
  if (level === "tool_use") {
    try {
      const obj = JSON.parse(content);
      const name = obj.name ?? obj.type ?? "tool";
      const input = obj.input ? JSON.stringify(obj.input, null, 2) : "";
      return `[Tool: ${name}]\n${input}`;
    } catch {
      return content;
    }
  }
  return content;
}

export function ExecutionLogViewer({ logs, connStatus, execStatus }: ExecutionLogViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    if (isAtBottom) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
  }, [logs]);

  if (logs.length === 0 && connStatus === "idle") {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg bg-slate-900 text-sm text-slate-500">
        No execution started
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {/* Status bar */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-slate-500">
          {logs.length} lines
        </span>
        <span className={`text-xs font-medium ${
          connStatus === "live" ? "text-green-500" :
          connStatus === "connecting" ? "text-amber-500" :
          connStatus === "error" ? "text-red-500" :
          "text-slate-400"
        }`}>
          {connStatus === "live" ? "● Live" :
           connStatus === "connecting" ? "● Connecting..." :
           connStatus === "error" ? "● Reconnecting..." :
           connStatus === "closed" ? `● ${execStatus ?? "Done"}` : "●"}
        </span>
      </div>

      {/* Log window */}
      <div
        ref={containerRef}
        className="h-64 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs"
      >
        {logs.map((log) => (
          <div key={`${log.execution_id}-${log.sequence}`} className="flex gap-2">
            <span className="shrink-0 text-slate-600 w-6 text-right">{log.sequence}</span>
            <pre
              className={`whitespace-pre-wrap break-all ${LEVEL_COLORS[log.level] ?? "text-slate-200"}`}
            >
              {formatContent(log.level, log.content)}
            </pre>
          </div>
        ))}
        {connStatus === "live" && (
          <div className="flex gap-2 mt-1">
            <span className="shrink-0 w-6" />
            <span className="text-slate-500 animate-pulse">▋</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
