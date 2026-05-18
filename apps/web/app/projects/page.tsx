"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Project } from "@/types";
import { api } from "@/lib/api-client";
import { relativeTime } from "@/lib/utils";
import { CreateProjectModal } from "@/components/project/CreateProjectModal";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    api.projects.list()
      .then((r) => setProjects(r.projects))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(project: Project) {
    setProjects((prev) => [project, ...prev]);
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-5xl flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">AI Agent Control Plane</h1>
            <p className="text-sm text-slate-500">Orchestrate coding agents across your projects</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/settings"
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              Settings
            </Link>
            <button
              onClick={() => setShowCreate(true)}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              New Project
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {loading && <p className="text-slate-500">Loading projects...</p>}
        {error && <p className="text-red-600">{error}</p>}

        {!loading && projects.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 py-16 text-center">
            <p className="text-slate-500 mb-4">No projects yet</p>
            <button
              onClick={() => setShowCreate(true)}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Create your first project
            </button>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <h2 className="font-semibold text-slate-900">{project.name}</h2>
              {project.description && (
                <p className="mt-1 text-sm text-slate-500 line-clamp-2">{project.description}</p>
              )}
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                <code className="rounded bg-slate-100 px-1.5 py-0.5">{project.default_branch}</code>
                <span className="ml-auto">{relativeTime(project.updated_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      </main>

      {showCreate && (
        <CreateProjectModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
