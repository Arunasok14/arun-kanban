"use client";

import { TokenState } from "@/hooks/useExecutionStream";

interface TokenBudgetPanelProps {
  tokens: TokenState;
  execStatus: string | null;
}

export function TokenBudgetPanel({ tokens, execStatus }: TokenBudgetPanelProps) {
  const { input, output, costUsd, budgetUsd, exhausted } = tokens;

  // Only show if there's any data
  if (input === 0 && output === 0 && !budgetUsd) return null;

  const pct = budgetUsd && budgetUsd > 0 ? Math.min((costUsd / budgetUsd) * 100, 100) : null;
  const barColor = exhausted
    ? "bg-red-500"
    : pct !== null && pct > 80
    ? "bg-amber-500"
    : "bg-blue-500";

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Token Usage</span>
        {exhausted && (
          <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
            Budget exhausted
          </span>
        )}
      </div>

      {/* Cost / budget bar */}
      {budgetUsd && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-500">
            <span>${costUsd.toFixed(4)}</span>
            <span>/ ${budgetUsd.toFixed(2)}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${barColor}`}
              style={{ width: `${pct ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Token counts */}
      <div className="flex gap-4 text-xs text-slate-500">
        <span>↑ {input.toLocaleString()} in</span>
        <span>↓ {output.toLocaleString()} out</span>
        <span className="ml-auto font-medium text-slate-700">${costUsd.toFixed(4)}</span>
      </div>
    </div>
  );
}
