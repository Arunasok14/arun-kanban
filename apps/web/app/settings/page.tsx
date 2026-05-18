"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { AppSettings, ModelOption, AgentOption } from "@/types";

const CLAUDE_MODELS = [
  { id: "sonnet", label: "Claude Sonnet 4.6", description: "Best balance of speed and capability" },
  { id: "opus", label: "Claude Opus 4.6", description: "Most capable, slower and more expensive" },
  { id: "haiku", label: "Claude Haiku 4.5", description: "Fastest and most affordable" },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [defaultModel, setDefaultModel] = useState("sonnet");
  const [defaultAgent, setDefaultAgent] = useState("claude-code");
  const [budgetUsd, setBudgetUsd] = useState("2.00");
  const [openaiKey, setOpenaiKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [requireApproval, setRequireApproval] = useState(false);
  const [dockerSandbox, setDockerSandbox] = useState(false);

  // Stage model state
  const [stageModelPlan, setStageModelPlan] = useState("opus");
  const [stageModelInProgress, setStageModelInProgress] = useState("sonnet");
  const [stageModelTesting, setStageModelTesting] = useState("haiku");

  // Deployment state
  const [githubToken, setGithubToken] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [showGithubToken, setShowGithubToken] = useState(false);
  const [vercelToken, setVercelToken] = useState("");
  const [vercelProjectId, setVercelProjectId] = useState("");
  const [showVercelToken, setShowVercelToken] = useState(false);
  const [autoDeploy, setAutoDeploy] = useState(false);

  // Policies state (managed separately from main form)
  type PolicyRow = { id: string; pattern: string; action: string; message: string; enabled: boolean };
  const [policies, setPolicies] = useState<PolicyRow[]>([]);
  const [newPattern, setNewPattern] = useState("");
  const [newAction, setNewAction] = useState("warn");
  const [newMessage, setNewMessage] = useState("");
  const [addingPolicy, setAddingPolicy] = useState(false);

  useEffect(() => {
    api.policies.list().then((r) => setPolicies(r.policies)).catch(() => {});
  }, []);

  async function handlePolicyToggle(id: string, enabled: boolean) {
    await api.policies.update(id, { enabled });
    setPolicies((prev) => prev.map((p) => (p.id === id ? { ...p, enabled } : p)));
  }

  async function handlePolicyDelete(id: string) {
    await api.policies.delete(id);
    setPolicies((prev) => prev.filter((p) => p.id !== id));
  }

  async function handlePolicyAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newPattern.trim() || !newMessage.trim()) return;
    setAddingPolicy(true);
    try {
      const created = await api.policies.create({ pattern: newPattern, action: newAction, message: newMessage });
      setPolicies((prev) => [...prev, created as PolicyRow]);
      setNewPattern(""); setNewMessage(""); setNewAction("warn");
    } catch {
      // ignore
    } finally {
      setAddingPolicy(false);
    }
  }

  useEffect(() => {
    Promise.all([api.settings.get(), api.settings.models(), api.settings.agents()])
      .then(([s, m, a]) => {
        setSettings(s);
        setModels(m.models);
        setAgents(a.agents);
        setDefaultModel(s.default_model);
        setDefaultAgent(s.default_agent);
        setBudgetUsd(s.default_budget_usd);
        setRequireApproval(s.require_approval ?? false);
        setDockerSandbox(s.docker_sandbox ?? false);
        setStageModelPlan(s.stage_model_plan ?? "opus");
        setStageModelInProgress(s.stage_model_in_progress ?? "sonnet");
        setStageModelTesting(s.stage_model_testing ?? "haiku");
        setGithubRepo(s.github_repo ?? "");
        setAutoDeploy(s.auto_deploy ?? false);
        setVercelProjectId(s.vercel_project_id ?? "");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const update: Record<string, string | number | boolean> = {
        default_model: defaultModel,
        default_agent: defaultAgent,
        default_budget_usd: budgetUsd,
        require_approval: requireApproval,
        docker_sandbox: dockerSandbox,
        github_repo: githubRepo,
        auto_deploy: autoDeploy,
        vercel_project_id: vercelProjectId,
        stage_model_plan: stageModelPlan,
        stage_model_in_progress: stageModelInProgress,
        stage_model_testing: stageModelTesting,
      };
      if (githubToken !== "") update.github_token = githubToken;
      if (vercelToken !== "") update.vercel_token = vercelToken;
      if (openaiKey !== "") update.openai_api_key = openaiKey;
      if (geminiKey !== "") update.gemini_api_key = geminiKey;

      const updated = await api.settings.update(update);
      setSettings(updated);
      setOpenaiKey(""); // Clear after save (don't keep plaintext in state)
      setGeminiKey("");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-500">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-3xl flex items-center gap-3">
          <Link href="/projects" className="text-sm text-slate-500 hover:text-slate-700">
            ← Projects
          </Link>
          <span className="text-slate-300">/</span>
          <h1 className="text-base font-semibold text-slate-900">Settings</h1>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <form onSubmit={handleSave} className="space-y-8">

          {/* ── Section 1: Default Agent ─────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Default Agent</h2>
              <p className="text-sm text-slate-500 mt-0.5">Choose which AI agent runs tasks by default</p>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                {agents.map((agent) => (
                  <label
                    key={agent.id}
                    className={`relative flex cursor-pointer flex-col rounded-lg border-2 p-4 transition-colors ${
                      defaultAgent === agent.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="default_agent"
                      value={agent.id}
                      checked={defaultAgent === agent.id}
                      onChange={() => setDefaultAgent(agent.id)}
                      className="sr-only"
                    />
                    <span className="font-medium text-sm text-slate-900">{agent.label}</span>
                    {defaultAgent === agent.id && (
                      <span className="mt-1 text-xs text-blue-600">Selected</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          </section>

          {/* ── Section 2: Stage Models ──────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Stage Models</h2>
              <p className="text-sm text-slate-500 mt-0.5">Choose which Claude model runs at each pipeline stage</p>
            </div>
            <div className="px-6 py-5 space-y-4">
              {[
                { label: "Plan", description: "Generate and revise implementation plans", value: stageModelPlan, setter: setStageModelPlan, accent: "border-l-purple-400" },
                { label: "In Progress", description: "Write code and implement features", value: stageModelInProgress, setter: setStageModelInProgress, accent: "border-l-blue-500" },
                { label: "Testing", description: "Run and verify tests", value: stageModelTesting, setter: setStageModelTesting, accent: "border-l-amber-400" },
              ].map(({ label, description, value, setter, accent }) => (
                <div key={label} className={`flex items-center justify-between rounded-lg border border-slate-200 border-l-4 ${accent} px-4 py-3`}>
                  <div>
                    <p className="text-sm font-medium text-slate-900">{label}</p>
                    <p className="text-xs text-slate-500">{description}</p>
                  </div>
                  <select
                    value={value}
                    onChange={(e) => setter(e.target.value)}
                    className="ml-4 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {CLAUDE_MODELS.map((m) => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>
              ))}
              <p className="text-xs text-slate-400">Fallback model for unmatched stages: <span className="font-medium">{CLAUDE_MODELS.find(m => m.id === defaultModel)?.label ?? defaultModel}</span></p>
            </div>
          </section>

          {/* ── Section 3: Budget Cap ────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Budget Cap</h2>
              <p className="text-sm text-slate-500 mt-0.5">Maximum spend per execution (USD). Claude stops when this is reached.</p>
            </div>
            <div className="px-6 py-5">
              <div className="flex items-center gap-2 w-48">
                <span className="text-slate-500">$</span>
                <input
                  type="number"
                  min="0.10"
                  max="100"
                  step="0.50"
                  value={budgetUsd}
                  onChange={(e) => setBudgetUsd(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-slate-500 text-sm">USD</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">Recommended: $2–$5 for most tasks</p>
            </div>
          </section>

          {/* ── Section 4: Safety & Approval ───────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Safety &amp; Approval</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Require human approval before the agent performs file writes, shell commands, or other operations.
              </p>
            </div>
            <div className="px-6 py-5">
              <label className="flex items-center gap-3 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={requireApproval}
                    onChange={(e) => setRequireApproval(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-200 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                  <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
                </div>
                <div>
                  <span className="text-sm font-medium text-slate-900">Require Human Approval</span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    When enabled, an approval popup appears in the task panel for each agent operation.
                    Auto-denied after 5 minutes of no response.
                  </p>
                </div>
              </label>
            </div>
          </section>

          {/* ── Section 5: API Keys ──────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">API Keys</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Required for Codex and Gemini agents (Phase 2). Claude Code uses its own auth via <code className="text-xs bg-slate-100 px-1 rounded">claude login</code>.
              </p>
            </div>
            <div className="px-6 py-5 space-y-5">

              {/* OpenAI */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-700">
                    OpenAI API Key
                    <span className="ml-2 text-xs font-normal text-slate-400">(for Codex CLI)</span>
                  </label>
                  {settings?.openai_api_key_set && (
                    <span className="text-xs text-green-600 font-medium">● Key saved</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type={showOpenaiKey ? "text" : "password"}
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder={settings?.openai_api_key_set ? "••••••••••••• (leave blank to keep existing)" : "sk-..."}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowOpenaiKey((v) => !v)}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
                  >
                    {showOpenaiKey ? "Hide" : "Show"}
                  </button>
                  {settings?.openai_api_key_set && (
                    <button
                      type="button"
                      onClick={() => setOpenaiKey("")}
                      className="rounded-lg border border-red-200 px-3 py-2 text-xs text-red-500 hover:bg-red-50"
                      title="Clear saved key"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Gemini */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-700">
                    Gemini API Key
                    <span className="ml-2 text-xs font-normal text-slate-400">(for Gemini CLI)</span>
                  </label>
                  {settings?.gemini_api_key_set && (
                    <span className="text-xs text-green-600 font-medium">● Key saved</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type={showGeminiKey ? "text" : "password"}
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder={settings?.gemini_api_key_set ? "••••••••••••• (leave blank to keep existing)" : "AIza..."}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGeminiKey((v) => !v)}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
                  >
                    {showGeminiKey ? "Hide" : "Show"}
                  </button>
                  {settings?.gemini_api_key_set && (
                    <button
                      type="button"
                      onClick={() => setGeminiKey("")}
                      className="rounded-lg border border-red-200 px-3 py-2 text-xs text-red-500 hover:bg-red-50"
                      title="Clear saved key"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              <p className="text-xs text-slate-400 bg-slate-50 rounded-lg px-3 py-2">
                Keys are stored in the local SQLite database. For production deployments, use a secrets manager (Vault, Doppler).
              </p>
            </div>
          </section>

          {/* ── Section 6: Policies ─────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Policies</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Rules evaluated before every agent operation. <strong>Deny</strong> blocks immediately;{" "}
                <strong>Warn</strong> requires human approval.
              </p>
            </div>
            <div className="px-6 py-5 space-y-3">
              {/* Built-in policies (read-only display) */}
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Built-in (always active)</p>
              {[
                { pattern: "DROP TABLE (non-test)", action: "deny", message: "Dropping production tables is not allowed." },
                { pattern: "rm -rf outside /workspace", action: "deny", message: "Deleting files outside the workspace." },
                { pattern: "git push --force", action: "warn", message: "Force push requires approval." },
                { pattern: "curl|wget piped to shell", action: "warn", message: "Remote script execution requires approval." },
                { pattern: "chmod 777", action: "deny", message: "World-writable permissions not allowed." },
              ].map((p, i) => (
                <div key={i} className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs">
                  <span className={`font-medium px-1.5 py-0.5 rounded text-xs ${p.action === "deny" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    {p.action}
                  </span>
                  <span className="font-mono text-slate-600 flex-1">{p.pattern}</span>
                  <span className="text-slate-400 truncate max-w-[200px]">{p.message}</span>
                </div>
              ))}

              {/* User-defined policies */}
              {policies.length > 0 && (
                <>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 pt-2">Custom</p>
                  {policies.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-xs">
                      <label className="relative cursor-pointer shrink-0">
                        <input
                          type="checkbox"
                          checked={p.enabled}
                          onChange={(e) => handlePolicyToggle(p.id, e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-8 h-4 bg-slate-200 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                        <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                      </label>
                      <span className={`font-medium px-1.5 py-0.5 rounded ${p.action === "deny" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                        {p.action}
                      </span>
                      <span className="font-mono text-slate-600 flex-1 truncate">{p.pattern}</span>
                      <span className="text-slate-400 truncate max-w-[160px]">{p.message}</span>
                      <button
                        type="button"
                        onClick={() => handlePolicyDelete(p.id)}
                        className="text-red-400 hover:text-red-600 ml-1"
                        title="Delete"
                      >✕</button>
                    </div>
                  ))}
                </>
              )}

              {/* Add custom policy */}
              <details className="pt-2">
                <summary className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer select-none">+ Add custom policy</summary>
                <form onSubmit={handlePolicyAdd} className="mt-3 space-y-2">
                  <div className="flex gap-2">
                    <select
                      value={newAction}
                      onChange={(e) => setNewAction(e.target.value)}
                      className="rounded border border-slate-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="warn">Warn</option>
                      <option value="deny">Deny</option>
                    </select>
                    <input
                      type="text"
                      value={newPattern}
                      onChange={(e) => setNewPattern(e.target.value)}
                      placeholder="Regex pattern (e.g. rm -rf /)"
                      className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Message shown when triggered"
                      className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                    <button
                      type="submit"
                      disabled={addingPolicy}
                      className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {addingPolicy ? "Adding..." : "Add"}
                    </button>
                  </div>
                </form>
              </details>
            </div>
          </section>

          {/* ── Section 7: Deployment ───────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Deployment</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Auto-create a GitHub PR and optionally trigger a Vercel preview after tests pass.
              </p>
            </div>
            <div className="px-6 py-5 space-y-5">

              {/* GitHub */}
              <div>
                <h3 className="text-sm font-medium text-slate-700 mb-3">GitHub</h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-sm text-slate-600">Personal Access Token</label>
                      {settings?.github_token_set && (
                        <span className="text-xs text-green-600 font-medium">● Saved</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type={showGithubToken ? "text" : "password"}
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        placeholder={settings?.github_token_set ? "••••••••••••• (leave blank to keep)" : "ghp_..."}
                        className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button type="button" onClick={() => setShowGithubToken((v) => !v)}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50">
                        {showGithubToken ? "Hide" : "Show"}
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">Needs <code className="bg-slate-100 px-1 rounded">repo</code> scope.</p>
                  </div>
                  <div>
                    <label className="text-sm text-slate-600 block mb-1.5">Repository <span className="text-slate-400 text-xs">(owner/repo)</span></label>
                    <input
                      type="text"
                      value={githubRepo}
                      onChange={(e) => setGithubRepo(e.target.value)}
                      placeholder="acme/my-app"
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              <hr className="border-slate-100" />

              {/* Vercel */}
              <div>
                <h3 className="text-sm font-medium text-slate-700 mb-3">Vercel Preview</h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-sm text-slate-600">Vercel API Token</label>
                      {settings?.vercel_token_set && (
                        <span className="text-xs text-green-600 font-medium">● Saved</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type={showVercelToken ? "text" : "password"}
                        value={vercelToken}
                        onChange={(e) => setVercelToken(e.target.value)}
                        placeholder={settings?.vercel_token_set ? "••••••••••••• (leave blank to keep)" : "vercel_..."}
                        className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button type="button" onClick={() => setShowVercelToken((v) => !v)}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50">
                        {showVercelToken ? "Hide" : "Show"}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-slate-600 block mb-1.5">Project ID</label>
                    <input
                      type="text"
                      value={vercelProjectId}
                      onChange={(e) => setVercelProjectId(e.target.value)}
                      placeholder="prj_..."
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <div className="relative">
                      <input type="checkbox" checked={autoDeploy} onChange={(e) => setAutoDeploy(e.target.checked)} className="sr-only peer" />
                      <div className="w-10 h-5 bg-slate-200 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                      <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-slate-900">Auto-deploy preview on test pass</span>
                      <p className="text-xs text-slate-500 mt-0.5">Triggers a Vercel preview deployment automatically when all tests pass.</p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </section>

          {/* ── Section 8: Docker Sandbox ─────────────────────────────────── */}
          <section className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">Docker Sandbox</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Run each agent inside an isolated Docker container with memory and CPU limits.
                Recommended for production. Requires Docker Desktop and the{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">kanban-agent</code> image.
              </p>
            </div>
            <div className="px-6 py-5 space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={dockerSandbox}
                    onChange={(e) => setDockerSandbox(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-200 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                  <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
                </div>
                <div>
                  <span className="text-sm font-medium text-slate-900">Use Docker Sandbox</span>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Agents run in a container with 2 GB RAM limit and 50% CPU cap.
                    Falls back to host execution if Docker is unavailable.
                  </p>
                </div>
              </label>
              {dockerSandbox && (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800 space-y-1">
                  <p className="font-medium">Setup required</p>
                  <ol className="list-decimal pl-4 space-y-0.5">
                    <li>Install Docker: <code className="bg-amber-100 px-1 rounded">brew install --cask docker</code></li>
                    <li>Build the agent image from the repo root:
                      <code className="block bg-amber-100 px-1 rounded mt-0.5">
                        docker build -f Dockerfile.agent -t kanban-agent:latest .
                      </code>
                    </li>
                    <li>Start Docker Desktop, then save these settings</li>
                  </ol>
                </div>
              )}
            </div>
          </section>

          {/* ── Save bar ─────────────────────────────────────────────────── */}
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-6 py-4">
            {error && <p className="text-sm text-red-600">{error}</p>}
            {saved && <p className="text-sm text-green-600 font-medium">Settings saved</p>}
            {!error && !saved && <span />}
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
