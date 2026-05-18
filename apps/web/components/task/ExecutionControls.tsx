"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { Task, Execution, ModelOption } from "@/types";
import { useBoardStore } from "@/store/boardStore";

const CLAUDE_MODELS = [
  { id: "sonnet", label: "Sonnet 4.6" },
  { id: "opus",   label: "Opus 4.6" },
  { id: "haiku",  label: "Haiku 4.5" },
  { id: "codex",  label: "Codex CLI" },
  { id: "gemini", label: "Gemini CLI" },
];

interface ExecutionControlsProps {
  task: Task;
  onExecutionStarted: (execution: Execution) => void;
}

export function ExecutionControls({ task, onExecutionStarted }: ExecutionControlsProps) {
  const updateTask = useBoardStore((s) => s.updateTask);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelOverride, setModelOverride] = useState<string>("");     // "" = use global default
  const [defaultModel, setDefaultModel] = useState<string>("sonnet"); // loaded from settings

  useEffect(() => {
    api.settings.get()
      .then((s) => setDefaultModel(s.default_model))
      .catch(() => {/* non-critical */});
  }, []);

  const execStatus = task.latest_execution?.status;
  const isRunning = execStatus === "running" || execStatus === "pending";

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const payload: { model_override?: string } = {};
      if (modelOverride) payload.model_override = modelOverride;
      const execution = await api.executions.start(task.id, payload);
      updateTask(task.id, {
        latest_execution: { id: execution.id, status: execution.status, started_at: execution.started_at },
      });
      onExecutionStarted(execution);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start execution");
    } finally {
      setLoading(false);
    }
  }

  async function handleStop() {
    if (!task.latest_execution?.id) return;
    setLoading(true);
    setError(null);
    try {
      await api.executions.stop(task.latest_execution.id);
      updateTask(task.id, { latest_execution: { ...task.latest_execution, status: "stopped" } });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to stop execution");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Model selector (only shown when not running) */}
      {!isRunning && (
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 shrink-0">Model</label>
          <select
            value={modelOverride}
            onChange={(e) => setModelOverride(e.target.value)}
            className="flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Default ({defaultModel})</option>
            {CLAUDE_MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
      )}

      {/* Run / Stop button */}
      <div className="flex items-center gap-2">
        {isRunning ? (
          <button
            onClick={handleStop}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            <span className="h-2 w-2 rounded-full bg-white animate-pulse" />
            {loading ? "Stopping..." : "Stop Agent"}
          </button>
        ) : (
          <button
            onClick={handleStart}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            </svg>
            {loading ? "Starting..." : "Run Agent"}
          </button>
        )}

        {execStatus && (
          <span className="text-sm text-slate-500 capitalize">{execStatus.replace("_", " ")}</span>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
