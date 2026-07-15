import { create } from "zustand";

export type WorkbenchSection =
  | "projects"
  | "overview"
  | "assets"
  | "characters"
  | "scenes"
  | "shots"
  | "production"
  | "timeline"
  | "tasks"
  | "media"
  | "settings";

interface WorkbenchState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
}));
