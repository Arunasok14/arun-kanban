"use client";

import { useState } from "react";
import { Droppable } from "@hello-pangea/dnd";
import { Task, TaskStatus } from "@/types";
import { TaskCard } from "./TaskCard";
import { AddTaskModal } from "./AddTaskModal";
import { COLUMN_LABELS, COLUMN_MARKER_COLORS } from "@/lib/constants";

interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  projectId: string;
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
}

export function KanbanColumn({ status, tasks, projectId, selectedTaskId, onSelectTask }: KanbanColumnProps) {
  const [showAddModal, setShowAddModal] = useState(false);

  return (
    <div className={`flex w-72 min-w-[288px] shrink-0 flex-col rounded-xl bg-slate-50 border border-slate-200 border-t-2 ${COLUMN_MARKER_COLORS[status]}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-700">{COLUMN_LABELS[status]}</h3>
          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600">
            {tasks.length}
          </span>
        </div>
        {status === "backlog" && (
          <button
            onClick={() => setShowAddModal(true)}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
            title="Add task"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>

      {/* Cards */}
      <Droppable droppableId={status}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`flex flex-1 flex-col gap-2 p-3 min-h-24 transition-colors ${
              snapshot.isDraggingOver ? "bg-blue-50" : ""
            }`}
          >
            {tasks.map((task, index) => (
              <TaskCard
                key={task.id}
                task={task}
                index={index}
                isSelected={selectedTaskId === task.id}
                onSelect={onSelectTask}
              />
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>

      {showAddModal && (
        <AddTaskModal projectId={projectId} onClose={() => setShowAddModal(false)} />
      )}
    </div>
  );
}
