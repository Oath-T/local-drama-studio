import { create } from "zustand";

export type WorkbenchSection = "projects" | "characters" | "scenes" | "shots" | "tasks";

interface WorkbenchState {
  activeSection: WorkbenchSection;
  sidebarCollapsed: boolean;
  setActiveSection: (section: WorkbenchSection) => void;
  toggleSidebar: () => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  activeSection: "projects",
  sidebarCollapsed: false,
  setActiveSection: (section) => set({ activeSection: section }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
}));
