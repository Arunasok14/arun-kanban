"use client";

import { useEffect, use } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { useBoardStore } from "@/store/boardStore";
import { KanbanBoard } from "@/components/board/KanbanBoard";

interface PageProps {
  params: Promise<{ projectId: string }>;
}

export default function BoardPage({ params }: PageProps) {
  const { projectId } = use(params);
  const setTasks = useBoardStore((s) => s.setTasks);
  const setLoading = useBoardStore((s) => s.setLoading);
  const setError = useBoardStore((s) => s.setError);
  const error = useBoardStore((s) => s.error);

  useEffect(() => {
    setLoading(true);
    api.tasks
      .list(projectId)
      .then((r) => setTasks(r.tasks))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId, setTasks, setLoading, setError]);

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* Top nav */}
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-6 py-3">
        <Link href="/projects" className="text-sm text-slate-500 hover:text-slate-700">
          ← Projects
        </Link>
        <span className="text-slate-300">/</span>
        <span className="text-sm font-medium text-slate-800">Board</span>
        <code className="ml-auto rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{projectId.slice(0, 8)}</code>
      </header>

      {/* Board */}
      <main className="flex-1 overflow-hidden p-4">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <KanbanBoard projectId={projectId} />
      </main>
    </div>
  );
}
