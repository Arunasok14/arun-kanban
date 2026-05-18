"use client";

import { useState } from "react";
import { DragDropContext, DropResult } from "@hello-pangea/dnd";
import { Task, TaskStatus } from "@/types";
import { KanbanColumn } from "./KanbanColumn";
import { TaskDetailPanel } from "@/components/task/TaskDetailPanel";
import { useBoardStore, tasksByStatus } from "@/store/boardStore";
import { api } from "@/lib/api-client";
import { COLUMN_ORDER } from "@/lib/constants";

interface KanbanBoardProps {
  projectId: string;
}

export function KanbanBoard({ projectId }: KanbanBoardProps) {
  const tasks = useBoardStore((s) => s.tasks);
  const selectedTaskId = useBoardStore((s) => s.selectedTaskId);
  const selectTask = useBoardStore((s) => s.selectTask);
  const moveTask = useBoardStore((s) => s.moveTask);
  const updateTask = useBoardStore((s) => s.updateTask);
  const isLoading = useBoardStore((s) => s.isLoading);
  const [toast, setToast] = useState<string | null>(null);

  const selectedTask = selectedTaskId ? tasks[selectedTaskId] : null;

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  async function onDragEnd(result: DropResult) {
    const { destination, source, draggableId } = result;
    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const srcIdx = COLUMN_ORDER.indexOf(source.droppableId as TaskStatus);
    const dstIdx = COLUMN_ORDER.indexOf(destination.droppableId as TaskStatus);

    // Block moving right by more than 1 stage
    if (dstIdx - srcIdx > 1) {
      showToast("Can't skip stages — move right one step at a time");
      return;
    }

    const newStatus = destination.droppableId as TaskStatus;
    const snapshot = moveTask(draggableId, newStatus, destination.index);

    try {
      const updated = await api.tasks.update(draggableId, { status: newStatus, position: destination.index });
      updateTask(draggableId, updated);
    } catch {
      if (snapshot) {
        updateTask(draggableId, snapshot);
      }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading board...</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-lg bg-slate-800 px-4 py-2.5 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}

      <div className="flex h-full gap-4">
        {/* Board columns */}
        <DragDropContext onDragEnd={onDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4 flex-1">
            {COLUMN_ORDER.map((status) => (
              <KanbanColumn
                key={status}
                status={status}
                tasks={tasksByStatus(tasks, status)}
                projectId={projectId}
                selectedTaskId={selectedTaskId}
                onSelectTask={selectTask}
              />
            ))}
          </div>
        </DragDropContext>

        {/* Task detail panel */}
        {selectedTask && (
          <div className="w-96 shrink-0 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <TaskDetailPanel task={selectedTask} onClose={() => selectTask(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
