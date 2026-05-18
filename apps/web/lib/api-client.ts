import { Project, Task, Execution, LogEntry, AppSettings, SettingsUpdate, ModelOption, AgentOption } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// ── Projects ──────────────────────────────────────────────────────────────────

export const api = {
  projects: {
    list: (): Promise<{ projects: Project[] }> => request("/api/v1/projects"),
    create: (data: { name: string; description?: string; repo_path: string; default_branch?: string }): Promise<Project> =>
      request("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string): Promise<Project> => request(`/api/v1/projects/${id}`),
    update: (id: string, data: Partial<Project>): Promise<Project> =>
      request(`/api/v1/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string): Promise<{ ok: boolean }> =>
      request(`/api/v1/projects/${id}`, { method: "DELETE" }),
  },

  tasks: {
    list: (projectId: string, status?: string): Promise<{ tasks: Task[] }> =>
      request(`/api/v1/projects/${projectId}/tasks${status ? `?status=${status}` : ""}`),
    create: (projectId: string, data: { title: string; description?: string; agent?: string }): Promise<Task> =>
      request(`/api/v1/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(data) }),
    get: (id: string): Promise<Task> => request(`/api/v1/tasks/${id}`),
    update: (id: string, data: { title?: string; description?: string; status?: string; position?: number; plan_content?: string | null; plan_approved_at?: string | null; plan_revision?: number }): Promise<Task> =>
      request(`/api/v1/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string): Promise<{ ok: boolean }> =>
      request(`/api/v1/tasks/${id}`, { method: "DELETE" }),
  },

  executions: {
    start: (taskId: string, data?: { prompt_override?: string; model_override?: string; budget_override?: number }): Promise<Execution> =>
      request(`/api/v1/tasks/${taskId}/executions`, { method: "POST", body: JSON.stringify(data ?? {}) }),
    get: (id: string): Promise<Execution> => request(`/api/v1/executions/${id}`),
    list: (taskId: string): Promise<{ executions: Execution[] }> =>
      request(`/api/v1/tasks/${taskId}/executions`),
    stop: (id: string): Promise<{ ok: boolean }> =>
      request(`/api/v1/executions/${id}/stop`, { method: "POST" }),
    logs: (id: string, afterSequence?: number): Promise<{ logs: LogEntry[]; has_more: boolean }> =>
      request(`/api/v1/executions/${id}/logs${afterSequence !== undefined ? `?after_sequence=${afterSequence}` : ""}`),
  },

  settings: {
    get: (): Promise<AppSettings> => request("/api/v1/settings"),
    update: (data: Partial<SettingsUpdate>): Promise<AppSettings> =>
      request("/api/v1/settings", { method: "PATCH", body: JSON.stringify(data) }),
    models: (): Promise<{ models: ModelOption[] }> => request("/api/v1/settings/models"),
    agents: (): Promise<{ agents: AgentOption[] }> => request("/api/v1/settings/agents"),
  },

  approvals: {
    list: (executionId: string): Promise<{ approvals: Array<{ id: string; status: string; prompt_text: string }> }> =>
      request(`/api/v1/executions/${executionId}/approvals`),
    decide: (approvalId: string, approved: boolean): Promise<{ ok: boolean; approved: boolean }> =>
      request(`/api/v1/approvals/${approvalId}/decide`, {
        method: "POST",
        body: JSON.stringify({ approved }),
      }),
  },

  policies: {
    list: (): Promise<{ policies: Array<{ id: string; pattern: string; action: string; message: string; enabled: boolean }> }> =>
      request("/api/v1/policies"),
    create: (data: { pattern: string; action: string; message: string }): Promise<{ id: string; pattern: string; action: string; message: string; enabled: boolean }> =>
      request("/api/v1/policies", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: { enabled?: boolean; pattern?: string; action?: string; message?: string }): Promise<{ id: string }> =>
      request(`/api/v1/policies/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string): Promise<{ ok: boolean }> =>
      request(`/api/v1/policies/${id}`, { method: "DELETE" }),
  },
};
