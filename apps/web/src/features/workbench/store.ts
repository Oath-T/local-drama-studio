import { create } from "zustand";

export type WorkbenchSection = "projects" | "characters" | "scenes" | "shots" | "tasks";

interface WorkbenchState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
}));
