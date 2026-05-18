"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { ApprovalRequest } from "@/types";

interface ApprovalPanelProps {
  approval: ApprovalRequest;
  onDecided: () => void;
}

const TIMEOUT_SECONDS = 300;

export function ApprovalPanel({ approval, onDecided }: ApprovalPanelProps) {
  const [deciding, setDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState(TIMEOUT_SECONDS);

  // Countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(interval);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  async function decide(approved: boolean) {
    setDeciding(true);
    setError(null);
    try {
      await api.approvals.decide(approval.approval_id, approved);
      onDecided();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit decision");
      setDeciding(false);
    }
  }

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const urgentColor = remaining < 60 ? "text-red-500" : "text-slate-400";

  return (
    <div className="rounded-lg border-2 border-amber-400 bg-amber-50 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
          <span className="text-sm font-semibold text-amber-900">Agent Approval Required</span>
        </div>
        <span className={`text-xs font-mono ${urgentColor}`}>
          {mins}:{secs.toString().padStart(2, "0")}
        </span>
      </div>

      {/* Prompt text */}
      <div className="rounded bg-white border border-amber-200 px-3 py-2">
        <p className="text-sm text-slate-800 font-mono leading-relaxed">{approval.prompt_text}</p>
      </div>

      {/* Auto-deny notice */}
      {remaining === 0 && (
        <p className="text-xs text-red-600">Timed out — operation was automatically denied.</p>
      )}

      {/* Action buttons */}
      {remaining > 0 && (
        <div className="flex gap-2">
          <button
            onClick={() => decide(true)}
            disabled={deciding}
            className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {deciding ? "Deciding..." : "Approve"}
          </button>
          <button
            onClick={() => decide(false)}
            disabled={deciding}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {deciding ? "Deciding..." : "Deny"}
          </button>
        </div>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
