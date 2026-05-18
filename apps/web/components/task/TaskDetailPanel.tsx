"use client";

import { useState, useEffect } from "react";
import { Task, Execution } from "@/types";
import { ExecutionLogViewer } from "./ExecutionLogViewer";
import { ExecutionControls } from "./ExecutionControls";
import { TokenBudgetPanel } from "./TokenBudgetPanel";
import { ApprovalPanel } from "./ApprovalPanel";
import { TestResultsPanel } from "./TestResultsPanel";
import { useExecutionStream } from "@/hooks/useExecutionStream";
import { STATUS_COLORS } from "@/lib/constants";
import { Badge } from "@/components/ui/Badge";
import { useBoardStore } from "@/store/boardStore";
import { api } from "@/lib/api-client";

interface TaskDetailPanelProps {
  task: Task;
  onClose: () => void;
}

export function TaskDetailPanel({ task, onClose }: TaskDetailPanelProps) {
  const updateTask = useBoardStore((s) => s.updateTask);
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(
    task.latest_execution?.id ?? null
  );
  const { logs, execStatus, connStatus, tokens, pendingApproval, testResults, deployment } = useExecutionStream(activeExecutionId);
  const [approvingPlan, setApprovingPlan] = useState(false);

  // When task's latest_execution changes externally, follow it
  useEffect(() => {
    if (task.latest_execution?.id && task.latest_execution.id !== activeExecutionId) {
      setActiveExecutionId(task.latest_execution.id);
    }
  }, [task.latest_execution?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleExecutionStarted(execution: Execution) {
    setActiveExecutionId(execution.id);
  }

  // Sync terminal WS status back to the board store so card reflects reality
  useEffect(() => {
    if (execStatus && task.latest_execution) {
      updateTask(task.id, {
        latest_execution: { ...task.latest_execution, status: execStatus },
      });
    }
  }, [execStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleApprovePlan() {
    setApprovingPlan(true);
    try {
      const updated = await api.tasks.update(task.id, {
        plan_approved_at: new Date().toISOString(),
        status: "in_progress",
      });
      updateTask(task.id, updated);
    } catch {
      // ignore
    } finally {
      setApprovingPlan(false);
    }
  }

  async function handleRequestRevision() {
    setApprovingPlan(true);
    try {
      const updated = await api.tasks.update(task.id, {
        plan_content: null,
        plan_revision: (task.plan_revision ?? 0) + 1,
      });
      updateTask(task.id, updated);
    } catch {
      // ignore
    } finally {
      setApprovingPlan(false);
    }
  }

  const hasPlan = task.status === "plan" || !!task.plan_content;
  const planApproved = !!task.plan_approved_at;
  const planPendingApproval = !!task.plan_content && !planApproved;
  const planDrafting = task.status === "plan" && !task.plan_content;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge className={STATUS_COLORS[task.status as keyof typeof STATUS_COLORS] ?? "bg-slate-100 text-slate-700"}>
              {task.status.replace("_", " ")}
            </Badge>
            <Badge className="bg-slate-100 text-slate-600">{task.agent}</Badge>
          </div>
          <h2 className="text-base font-semibold text-slate-900 leading-snug">{task.title}</h2>
        </div>
        <button
          onClick={onClose}
          className="ml-3 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {/* Description */}
        {task.description && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Description</h3>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{task.description}</p>
          </div>
        )}

        {/* Branch info */}
        {task.branch_name && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Branch</h3>
            <code className="text-xs text-slate-700 bg-slate-100 rounded px-2 py-1">{task.branch_name}</code>
          </div>
        )}

        {/* Plan artifact */}
        {hasPlan && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Plan</h3>
            {planDrafting && (
              <div className="rounded-lg border border-dashed border-purple-300 bg-purple-50 p-3 text-sm text-purple-700">
                No plan drafted yet. Run the agent to generate a plan.
              </div>
            )}
            {task.plan_content && (
              <div className={`rounded-lg border p-3 space-y-3 ${planApproved ? "border-green-200 bg-green-50" : "border-purple-200 bg-purple-50"}`}>
                {planApproved && (
                  <div className="flex items-center gap-1.5 text-xs font-medium text-green-700">
                    <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Approved — execution in progress
                  </div>
                )}
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto max-h-48">
                  {task.plan_content}
                </pre>
                {planPendingApproval && (
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={handleApprovePlan}
                      disabled={approvingPlan}
                      className="flex-1 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Approve & Start
                    </button>
                    <button
                      onClick={handleRequestRevision}
                      disabled={approvingPlan}
                      className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Request Revision
                    </button>
                  </div>
                )}
                {task.plan_revision > 0 && (
                  <p className="text-xs text-slate-400">Revision {task.plan_revision}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Execution controls */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Agent Control</h3>
          <ExecutionControls task={task} wsExecStatus={execStatus} onExecutionStarted={handleExecutionStarted} />
        </div>

        {/* Token budget */}
        {activeExecutionId && (
          <TokenBudgetPanel tokens={tokens} execStatus={execStatus} />
        )}

        {/* Human approval prompt */}
        {pendingApproval && (
          <ApprovalPanel
            approval={pendingApproval}
            onDecided={() => {/* dismissed via WS frame */}}
          />
        )}

        {/* Test results (from WS stream or persisted on task) */}
        <TestResultsPanel results={testResults ?? (task.test_results as Parameters<typeof TestResultsPanel>[0]["results"]) ?? null} />

        {/* Deployment links (live from WS or persisted on task) */}
        {(deployment?.prUrl || task.pr_url || deployment?.previewUrl || task.preview_url) && (
          <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Deployment</span>
            <div className="flex flex-wrap gap-2">
              {(deployment?.prUrl || task.pr_url) && (
                <a
                  href={deployment?.prUrl ?? task.pr_url ?? ""}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
                >
                  <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
                  </svg>
                  View Pull Request
                </a>
              )}
              {(deployment?.previewUrl || task.preview_url) && (
                <a
                  href={deployment?.previewUrl ?? task.preview_url ?? ""}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  Preview
                </a>
              )}
            </div>
          </div>
        )}

        {/* Live logs */}
        {activeExecutionId && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Execution Log</h3>
            <ExecutionLogViewer logs={logs} connStatus={connStatus} execStatus={execStatus} />
          </div>
        )}
      </div>
    </div>
  );
}
