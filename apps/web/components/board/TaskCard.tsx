"use client";

import { Draggable } from "@hello-pangea/dnd";
import { Task, TaskStatus } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { EXECUTION_STATUS_COLORS, STATUS_COLORS, COLUMN_ORDER, STAGE_INDEX, STAGE_DOT_COLORS } from "@/lib/constants";
import { relativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  task: Task;
  index: number;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function TaskCard({ task, index, isSelected, onSelect }: TaskCardProps) {
  const execStatus = task.latest_execution?.status;
  const testResults = task.test_results as { passed: number; failed: number; errors: number } | null | undefined;
  const hasTests = testResults && (testResults.passed > 0 || testResults.failed > 0 || testResults.errors > 0);
  const testsPassing = hasTests && testResults.failed === 0 && testResults.errors === 0;
  const stageIdx = STAGE_INDEX[task.status as TaskStatus] ?? 0;
  const stageDotColor = STAGE_DOT_COLORS[task.status as TaskStatus] ?? "bg-slate-400";

  // Stage-aware status pills
  const isPlanPending = task.status === "plan" && task.plan_content && !task.plan_approved_at;
  const isPlanDrafting = task.status === "plan" && !task.plan_content;
  const isTestingRunning = task.status === "testing" && execStatus === "running";
  const isTestingPassed = task.status === "testing" && hasTests && testsPassing;
  const isTestingFailed = task.status === "testing" && hasTests && !testsPassing;

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onSelect(task.id)}
          className={cn(
            "rounded-lg border bg-white p-3 shadow-sm cursor-pointer select-none transition-shadow",
            snapshot.isDragging && "shadow-lg rotate-1",
            isSelected && "ring-2 ring-blue-500"
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-slate-900 line-clamp-2 flex-1">{task.title}</p>
            {execStatus && (
              <span
                className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", EXECUTION_STATUS_COLORS[execStatus] ?? "bg-slate-300")}
                title={execStatus}
              />
            )}
          </div>

          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <Badge className="bg-slate-100 text-slate-600">{task.agent}</Badge>

            {/* Stage-aware pills */}
            {isPlanDrafting && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">Drafting</span>
            )}
            {isPlanPending && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 animate-pulse">Pending approval</span>
            )}
            {isTestingRunning && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 animate-pulse">Running tests</span>
            )}
            {isTestingPassed && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-green-100 text-green-700">Tests passed</span>
            )}
            {isTestingFailed && (
              <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-red-100 text-red-700">Tests failed</span>
            )}

            {/* Test count badge (non-testing stages) */}
            {hasTests && task.status !== "testing" && (
              <span
                className={cn(
                  "text-xs font-medium px-1.5 py-0.5 rounded",
                  testsPassing ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                )}
                title={`${testResults.passed} passed, ${testResults.failed} failed`}
              >
                {testsPassing ? `✓ ${testResults.passed}` : `✗ ${testResults.failed}`}
              </span>
            )}

            {task.pr_url && (
              <a
                href={task.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-xs font-medium text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded hover:bg-slate-200"
                title="View pull request"
              >
                PR
              </a>
            )}
            {task.preview_url && (
              <a
                href={task.preview_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-xs font-medium text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded hover:bg-blue-100"
                title="View preview"
              >
                Preview
              </a>
            )}
            <span className="text-xs text-slate-400 ml-auto">{relativeTime(task.updated_at)}</span>
          </div>

          {/* 5-dot stage track */}
          <div className="mt-2.5 flex items-center gap-1">
            {COLUMN_ORDER.map((s, i) => (
              <div
                key={s}
                className={cn(
                  "h-1.5 flex-1 rounded-full",
                  i <= stageIdx ? stageDotColor : "bg-slate-200"
                )}
              />
            ))}
          </div>
        </div>
      )}
    </Draggable>
  );
}
