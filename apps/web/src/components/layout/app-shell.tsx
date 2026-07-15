import {
  Boxes,
  BriefcaseBusiness,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Film,
  Images,
  LayoutList,
  ListChecks,
  Route,
  Settings,
  StretchHorizontal,
  UserRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type React from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { HealthStatus } from "@/features/health/components/health-status";
import { type WorkbenchSection, useWorkbenchStore } from "@/features/workbench/store";
import { copy } from "@/locales";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
}

const navItems: Array<{
  id: WorkbenchSection;
  label: string;
  path: string;
  icon: LucideIcon;
  projectPath?: (projectId: string) => string;
  indent?: boolean;
}> = [
  { id: "projects", label: copy.nav.projects, path: "/projects", icon: BriefcaseBusiness },
  {
    id: "overview",
    label: "项目总览",
    path: "/projects",
    icon: LayoutList,
    projectPath: (projectId) => `/projects/${projectId}`
  },
  {
    id: "assets",
    label: "资产库",
    path: "/projects",
    icon: Boxes,
    projectPath: (projectId) => `/projects/${projectId}/assets`
  },
  {
    id: "characters",
    label: "角色库",
    path: "/characters",
    icon: UserRound,
    projectPath: (projectId) => `/projects/${projectId}/characters`,
    indent: true
  },
  {
    id: "scenes",
    label: "场景库",
    path: "/scenes",
    icon: Images,
    projectPath: (projectId) => `/projects/${projectId}/scenes`,
    indent: true
  },
  {
    id: "shots",
    label: "镜头工作台",
    path: "/shots",
    icon: Clapperboard,
    projectPath: (projectId) => `/projects/${projectId}/shots`
  },
  {
    id: "production",
    label: "生产看板",
    path: "/tasks",
    icon: Route,
    projectPath: (projectId) => `/projects/${projectId}/production`
  },
  {
    id: "timeline",
    label: "时间线与导出",
    path: "/tasks",
    icon: StretchHorizontal,
    projectPath: (projectId) => `/projects/${projectId}/timeline`
  },
  {
    id: "tasks",
    label: "生成中心",
    path: "/tasks",
    icon: ListChecks,
    projectPath: (projectId) => `/projects/${projectId}/generation`
  },
  {
    id: "media",
    label: "媒体库",
    path: "/media",
    icon: Film,
    projectPath: (projectId) => `/projects/${projectId}/media`
  },
  {
    id: "settings",
    label: "设置",
    path: "/settings",
    icon: Settings,
    projectPath: (projectId) => `/projects/${projectId}/settings`
  }
];

export function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const sidebarCollapsed = useWorkbenchStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useWorkbenchStore((state) => state.toggleSidebar);
  const projectMatch = location.pathname.match(/^\/projects\/([^/]+)/);
  const currentProjectId = projectMatch?.[1];
  const activeSection = location.pathname.includes("/characters")
    ? "characters"
    : location.pathname.includes("/scenes")
      ? "scenes"
      : location.pathname.includes("/shots")
        ? "shots"
        : location.pathname.includes("/production")
          ? "production"
          : location.pathname.includes("/timeline")
          ? "timeline"
          : location.pathname.includes("/generation") || location.pathname.startsWith("/tasks")
          ? "tasks"
          : location.pathname.includes("/media") || location.pathname.startsWith("/media")
            ? "media"
            : location.pathname.includes("/settings") || location.pathname.startsWith("/settings")
              ? "settings"
              : location.pathname.includes("/assets")
                ? "assets"
                : currentProjectId
                  ? "overview"
                  : navItems.find((item) => location.pathname.startsWith(item.path))?.id;

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
            <div className="text-xs text-muted">{copy.app.subtitle}</div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            title={sidebarCollapsed ? copy.app.expandSidebar : copy.app.collapseSidebar}
            aria-label={sidebarCollapsed ? copy.app.expandSidebar : copy.app.collapseSidebar}
            onClick={toggleSidebar}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>

        <nav className="flex-1 space-y-1 p-2" aria-label={copy.app.mainNavigation}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                type="button"
                title={sidebarCollapsed ? item.label : undefined}
                aria-current={isActive ? "page" : undefined}
                onClick={() => {
                  const path =
                    item.projectPath && currentProjectId
                      ? item.projectPath(currentProjectId)
                      : item.path;
                  navigate(path);
                }}
                className={cn(
                  "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm transition-colors",
                  isActive
                    ? "bg-primarySoft text-foreground"
                    : "text-muted hover:bg-panelRaised hover:text-foreground",
                  item.indent && !sidebarCollapsed && "pl-8",
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
              <div className="truncate text-sm font-semibold">{copy.app.unnamedProject}</div>
              <div className="text-xs text-muted">{copy.app.workbenchFoundation}</div>
            </div>
          </div>
          <HealthStatus />
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto bg-background px-6 py-5">
          {children}
        </main>

        <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-panel px-4 text-xs text-muted">
          <span>{copy.app.taskStatusIdle}</span>
          <span>{copy.app.localMode}</span>
        </footer>
      </div>
    </div>
  );
}
