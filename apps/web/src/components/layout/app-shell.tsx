import {
  BriefcaseBusiness,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Images,
  LayoutList,
  ListChecks,
  UserRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type React from "react";

import { Button } from "@/components/ui/button";
import { HealthStatus } from "@/features/health/components/health-status";
import {
  type WorkbenchSection,
  useWorkbenchStore
} from "@/features/workbench/store";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
}

const navItems: Array<{
  id: WorkbenchSection;
  label: string;
  icon: LucideIcon;
}> = [
  { id: "projects", label: "项目", icon: BriefcaseBusiness },
  { id: "characters", label: "角色库", icon: UserRound },
  { id: "scenes", label: "场景库", icon: Images },
  { id: "shots", label: "镜头", icon: Clapperboard },
  { id: "tasks", label: "生成任务", icon: ListChecks }
];

export function AppShell({ children }: AppShellProps) {
  const activeSection = useWorkbenchStore((state) => state.activeSection);
  const sidebarCollapsed = useWorkbenchStore((state) => state.sidebarCollapsed);
  const setActiveSection = useWorkbenchStore((state) => state.setActiveSection);
  const toggleSidebar = useWorkbenchStore((state) => state.toggleSidebar);

  return (
    <div className="flex h-screen min-h-[768px] overflow-hidden bg-background text-foreground">
      <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-border bg-panel shadow-workbench transition-[width] duration-200",
          sidebarCollapsed ? "w-[72px]" : "w-[220px]"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-3">
          <div className={cn("min-w-0", sidebarCollapsed && "sr-only")}>
            <div className="text-sm font-semibold">Local Drama Studio</div>
            <div className="text-xs text-muted">本地短剧制作</div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            title={sidebarCollapsed ? "展开侧栏" : "折叠侧栏"}
            aria-label={sidebarCollapsed ? "展开侧栏" : "折叠侧栏"}
            onClick={toggleSidebar}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>

        <nav className="flex-1 space-y-1 p-2" aria-label="主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                type="button"
                title={sidebarCollapsed ? item.label : undefined}
                aria-current={isActive ? "page" : undefined}
                onClick={() => setActiveSection(item.id)}
                className={cn(
                  "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm transition-colors",
                  isActive
                    ? "bg-primarySoft text-foreground"
                    : "text-muted hover:bg-panelRaised hover:text-foreground",
                  sidebarCollapsed && "justify-center px-0"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className={cn(sidebarCollapsed && "sr-only")}>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-panel px-5 shadow-workbench">
          <div className="flex min-w-0 items-center gap-3">
            <LayoutList className="h-4 w-4 text-primary" aria-hidden="true" />
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">未命名项目</div>
              <div className="text-xs text-muted">Sprint 0 工作台地基</div>
            </div>
          </div>
          <HealthStatus />
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto bg-background px-6 py-5">
          {children}
        </main>

        <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-panel px-4 text-xs text-muted">
          <span>任务状态：空闲</span>
          <span>本地开发模式</span>
        </footer>
      </div>
    </div>
  );
}
