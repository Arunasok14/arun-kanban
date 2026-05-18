"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { LogEntry, WsFrame, ApprovalRequest } from "@/types";
import { WS_URL } from "@/lib/constants";

type ConnectionStatus = "idle" | "connecting" | "live" | "closed" | "error";

export interface TokenState {
  input: number;
  output: number;
  costUsd: number;
  budgetUsd: number | null;
  exhausted: boolean;
}

interface TestResults {
  passed: number;
  failed: number;
  errors: number;
  details: string[];
}

export function useExecutionStream(executionId: string | null) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [execStatus, setExecStatus] = useState<string | null>(null);
  const [connStatus, setConnStatus] = useState<ConnectionStatus>("idle");
  const [tokens, setTokens] = useState<TokenState>({ input: 0, output: 0, costUsd: 0, budgetUsd: null, exhausted: false });
  const [pendingApproval, setPendingApproval] = useState<ApprovalRequest | null>(null);
  const [testResults, setTestResults] = useState<TestResults | null>(null);
  const [deployment, setDeployment] = useState<{ prUrl: string | null; previewUrl: string | null } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const seqRef = useRef<number>(0);
  const doneRef = useRef<boolean>(false); // set when server sends "done" frame

  const connect = useCallback(() => {
    if (!executionId) return;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    setConnStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/executions/${executionId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnStatus("live");

    ws.onmessage = (e: MessageEvent) => {
      try {
        const frame: WsFrame = JSON.parse(e.data);

        if (frame.type === "log") {
          const entry: LogEntry = {
            id: frame.sequence ?? seqRef.current++,
            execution_id: executionId,
            sequence: frame.sequence ?? seqRef.current++,
            level: (frame.level ?? "stdout") as LogEntry["level"],
            content: frame.content ?? "",
            timestamp: frame.timestamp ?? new Date().toISOString(),
          };
          setLogs((prev) => {
            // Deduplicate by sequence
            const exists = prev.some((l) => l.sequence === entry.sequence);
            return exists ? prev : [...prev, entry];
          });
        } else if (frame.type === "status") {
          setExecStatus(frame.status ?? null);
          if (frame.token_input !== undefined) {
            setTokens(prev => ({
              ...prev,
              input: frame.token_input ?? prev.input,
              output: frame.token_output ?? prev.output,
              costUsd: frame.cost_usd ?? prev.costUsd,
            }));
          }
        } else if (frame.type === "tokens") {
          setTokens({
            input: frame.token_input ?? 0,
            output: frame.token_output ?? 0,
            costUsd: frame.cost_usd ?? 0,
            budgetUsd: frame.budget_usd ?? null,
            exhausted: frame.budget_exhausted ?? false,
          });
        } else if (frame.type === "approval_request") {
          setPendingApproval({
            approval_id: frame.approval_id ?? "",
            prompt_text: frame.prompt_text ?? "",
          });
        } else if (frame.type === "approval_decided" || frame.type === "approval_timeout") {
          setPendingApproval(null);
        } else if (frame.type === "test_results") {
          setTestResults({
            passed: frame.passed ?? 0,
            failed: frame.failed ?? 0,
            errors: frame.errors ?? 0,
            details: frame.details ?? [],
          });
        } else if (frame.type === "deployment") {
          setDeployment({
            prUrl: frame.pr_url ?? null,
            previewUrl: frame.preview_url ?? null,
          });
        } else if (frame.type === "done") {
          doneRef.current = true;
          setExecStatus(frame.status ?? null);
          setConnStatus("closed");
          setPendingApproval(null);
        }
        // ignore "ping"
      } catch {
        // ignore malformed frames
      }
    };

    ws.onerror = () => setConnStatus("error");

    ws.onclose = (e) => {
      // Don't reconnect if cleanly closed (server sent "done" frame)
      if (doneRef.current) return;
      setConnStatus("error");
      // Exponential backoff reconnect (max 10s)
      const delay = Math.min(1000 * (reconnectTimer.current ? 2 : 1), 10000);
      reconnectTimer.current = setTimeout(connect, delay);
    };
  }, [executionId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!executionId) {
      setLogs([]);
      setExecStatus(null);
      setConnStatus("idle");
      setTokens({ input: 0, output: 0, costUsd: 0, budgetUsd: null, exhausted: false });
      setPendingApproval(null);
      setTestResults(null);
      setDeployment(null);
      return;
    }
    setLogs([]);
    seqRef.current = 0;
    doneRef.current = false;
    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        wsRef.current.close();
      }
    };
  }, [executionId, connect]);

  return { logs, execStatus, connStatus, tokens, pendingApproval, testResults, deployment };
}
