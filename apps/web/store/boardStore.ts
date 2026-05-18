"use client";

import { create } from "zustand";
import { Task, TaskStatus } from "@/types";

interface BoardStore {
  tasks: Record<string, Task>;
  selectedTaskId: string | null;
  isLoading: boolean;
  error: string | null;

  setTasks: (tasks: Task[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  selectTask: (taskId: string | null) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, patch: Partial<Task>) => void;
  removeTask: (taskId: string) => void;
  moveTask: (taskId: string, status: TaskStatus, position: number) => Task | null;
}

export const useBoardStore = create<BoardStore>((set, get) => ({
  tasks: {},
  selectedTaskId: null,
  isLoading: false,
  error: null,

  setTasks: (tasks) => {
    const record: Record<string, Task> = {};
    tasks.forEach((t) => (record[t.id] = t));
    set({ tasks: record });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  selectTask: (taskId) => set({ selectedTaskId: taskId }),

  addTask: (task) =>
    set((state) => ({ tasks: { ...state.tasks, [task.id]: task } })),

  updateTask: (taskId, patch) =>
    set((state) => ({
      tasks: state.tasks[taskId]
        ? { ...state.tasks, [taskId]: { ...state.tasks[taskId], ...patch } }
        : state.tasks,
    })),

  removeTask: (taskId) =>
    set((state) => {
      const next = { ...state.tasks };
      delete next[taskId];
      return { tasks: next, selectedTaskId: state.selectedTaskId === taskId ? null : state.selectedTaskId };
    }),

  moveTask: (taskId, status, position) => {
    const prev = get().tasks[taskId];
    if (!prev) return null;
    const snapshot = { ...prev };
    set((state) => ({
      tasks: { ...state.tasks, [taskId]: { ...state.tasks[taskId], status, position } },
    }));
    return snapshot;
  },
}));

export const tasksByStatus = (tasks: Record<string, Task>, status: TaskStatus): Task[] =>
  Object.values(tasks)
    .filter((t) => t.status === status)
    .sort((a, b) => a.position - b.position);
