export type TaskStatus = "backlog" | "plan" | "in_progress" | "testing" | "done";

export interface ExecutionSummary {
  id: string;
  status: string;
  started_at: string | null;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  repo_path: string;
  default_branch: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  agent: string;
  position: number;
  branch_name: string | null;
  worktree_path: string | null;
  latest_execution: ExecutionSummary | null;
  test_results: { passed: number; failed: number; errors: number } | null;
  pr_url: string | null;
  preview_url: string | null;
  plan_content: string | null;
  plan_approved_at: string | null;
  plan_revision: number;
  created_at: string;
  updated_at: string;
}

export interface Execution {
  id: string;
  task_id: string;
  status: string;
  agent: string;
  pid: number | null;
  exit_code: number | null;
  started_at: string | null;
  finished_at: string | null;
  token_usage: { input: number; output: number; total: number } | null;
  error_message: string | null;
  created_at: string;
  token_input: number;
  token_output: number;
  cost_usd: number;
  budget_usd: number | null;
  budget_exhausted: boolean;
  execution_type: string;
}

export interface LogEntry {
  id: number;
  execution_id: string;
  sequence: number;
  level: "stdout" | "stderr" | "system" | "tool_use";
  content: string;
  timestamp: string;
}

export interface SettingsUpdate {
  default_model?: string;
  default_agent?: string;
  default_budget_usd?: string;
  openai_api_key?: string;
  gemini_api_key?: string;
  require_approval?: boolean;
  github_token?: string;
  github_repo?: string;
  vercel_token?: string;
  vercel_project_id?: string;
  auto_deploy?: boolean;
  docker_sandbox?: boolean;
  stage_model_plan?: string;
  stage_model_in_progress?: string;
  stage_model_testing?: string;
}

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  coming_soon?: boolean;
}

export interface AgentOption {
  id: string;
  label: string;
  status: "available" | "coming_soon";
}

export interface WsFrame {
  type: "log" | "status" | "done" | "ping" | "__done__" | "tokens" | "approval_request" | "approval_decided" | "approval_timeout" | "validation_started" | "test_results" | "deployment";
  sequence?: number;
  level?: string;
  content?: string;
  timestamp?: string;
  status?: string;
  pid?: number | null;
  exit_code?: number | null;
  token_usage?: { input: number; output: number; total: number } | null;
  // token tracking fields
  token_input?: number;
  token_output?: number;
  cost_usd?: number;
  budget_usd?: number | null;
  budget_exhausted?: boolean;
  // approval fields
  approval_id?: string;
  prompt_text?: string;
  approved?: boolean;
  // validation_started fields
  validation_execution_id?: string;
  // test_results fields
  passed?: number;
  failed?: number;
  errors?: number;
  details?: string[];
  // deployment fields
  pr_url?: string | null;
  preview_url?: string | null;
}

export interface ApprovalRequest {
  approval_id: string;
  prompt_text: string;
}

export interface AppSettings {
  default_model: string;
  default_agent: string;
  default_budget_usd: string;
  openai_api_key_set: boolean;
  gemini_api_key_set: boolean;
  require_approval: boolean;
  github_token_set: boolean;
  github_repo: string;
  vercel_token_set: boolean;
  vercel_project_id: string;
  auto_deploy: boolean;
  docker_sandbox: boolean;
  stage_model_plan: string;
  stage_model_in_progress: string;
  stage_model_testing: string;
}
