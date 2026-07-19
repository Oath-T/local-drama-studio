import {
  AlertTriangle,
  ChevronDown,
  Clapperboard,
  ExternalLink,
  Film,
  FolderKanban,
  Image,
  LayoutDashboard,
  Maximize2,
  Menu,
  Minimize2,
  PanelBottomOpen,
  PanelLeftClose,
  PanelRightClose,
  RefreshCcw,
  Settings,
  Sparkles,
  UserRound,
  Wand2,
  X
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode
} from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { characterKeys, fetchCharacters } from "@/features/characters/api";
import type { Character } from "@/features/characters/types";
import { fetchGenerationTasks, generationTaskKeys } from "@/features/generation-tasks/api";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import { fetchHealth } from "@/features/health/api";
import { fetchSystemCapabilities } from "@/features/keyframe-generation/api";
import { productionStatusKeys, fetchProjectProductionStatus } from "@/features/production-status/api";
import type { ProjectProductionStatus, ShotProductionStatus } from "@/features/production-status/types";
import { fetchProject, projectKeys } from "@/features/projects/api";
import type { Project } from "@/features/projects/types";
import { fetchScenes, sceneKeys } from "@/features/scenes/api";
import type { Scene } from "@/features/scenes/types";
import { fetchShots, shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
import { fetchProjectTimeline, timelineKeys } from "@/features/timeline/api";
import type { ProjectTimeline } from "@/features/timeline/types";
import { fetchVideoWorkflows } from "@/features/video-generation/api";
import { cn } from "@/lib/utils";
import {
  STUDIO_SHELL_DEFAULTS,
  STUDIO_SHELL_LIMITS,
  clamp,
  createDefaultStudioShellLayout,
  isEditableTarget,
  loadStudioShellLayout,
  saveStudioShellLayout,
  type ResizablePanel,
  type StudioShellLayoutState
} from "@/features/studio-ui/layout-state";
import { StudioStatusBadge } from "@/features/studio-ui/components/studio-status-badge";

import { buildStudioRecommendation, countAdoptedSteps, type StudioRecommendation } from "../recommendation";
import {
  buildRecentItems,
  buildStudioIssues,
  buildStudioStages,
  findProductionShot,
  type StudioIssue,
  type StudioRecentItem,
  type StudioStage
} from "../summary";
import {
  clearStudioSession,
  createDefaultStudioSession,
  loadStudioSession,
  parseStudioUrlContext,
  sanitizeStudioSessionSelection,
  saveStudioSession,
  type StudioBottomTab,
  type StudioContextEntityType,
  type StudioContextTab,
  type StudioInspectorTab,
  type StudioMode,
  type StudioSessionState,
  type StudioView
} from "../session";

interface DragSession {
  panel: ResizablePanel;
  startX: number;
  startY: number;
  startValue: number;
}

const navItems = [
  { id: "overview", label: "项目总览", icon: FolderKanban, href: (projectId: string) => `/projects/${projectId}/studio` },
  { id: "assets", label: "资产库", icon: Image, href: (projectId: string) => `/projects/${projectId}/assets` },
  { id: "shots", label: "镜头工作台", icon: Clapperboard, href: (projectId: string) => `/projects/${projectId}/shots` },
  { id: "generation", label: "生成中心", icon: Wand2, href: (projectId: string) => `/projects/${projectId}/generation` },
  { id: "media", label: "媒体库", icon: Film, href: (projectId: string) => `/projects/${projectId}/media` },
  { id: "settings", label: "设置", icon: Settings, href: (projectId: string) => `/projects/${projectId}/settings` }
] as const;

const viewTabs: Array<{ id: StudioView; label: string }> = [
  { id: "start", label: "续作起点" },
  { id: "storyboard", label: "故事板" },
  { id: "workflow", label: "工作流画布" },
  { id: "shot_console", label: "镜头生成控制台" }
];

const contextTabs: Array<{ id: StudioContextTab; label: string }> = [
  { id: "overview", label: "概览" },
  { id: "shots", label: "镜头" },
  { id: "assets", label: "素材" }
];

const inspectorTabs: Array<{ id: StudioInspectorTab; label: string }> = [
  { id: "info", label: "信息" },
  { id: "next", label: "下一步" }
];

const bottomTabs: Array<{ id: StudioBottomTab; label: string }> = [
  { id: "running", label: "运行任务" },
  { id: "issues", label: "问题" }
];

function getPanelWidth(layout: StudioShellLayoutState, panel: "left" | "right") {
  if (layout.focusMode) return 0;
  if (panel === "left") return layout.leftPanelCollapsed ? 0 : layout.leftWidth;
  return layout.rightPanelCollapsed ? 0 : layout.rightWidth;
}

function isPanelVisible(width: number) {
  return width > 0;
}

export function StudioWorkspacePage({ projectId }: { projectId: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [layout, setLayout] = useState<StudioShellLayoutState>(() =>
    loadStudioShellLayout(`studio:${projectId}`)
  );
  const [session, setSession] = useState<StudioSessionState>(() => loadStudioSession(projectId));
  const [viewportWidth, setViewportWidth] = useState(() => (typeof window === "undefined" ? 1440 : window.innerWidth));
  const [compactDrawer, setCompactDrawer] = useState<"left" | "right" | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [localNotice, setLocalNotice] = useState<string | null>(null);
  const [layoutSaveFailed, setLayoutSaveFailed] = useState(false);
  const [isSavingLayout, setIsSavingLayout] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const dragSessionRef = useRef<DragSession | null>(null);
  const layoutSaveTimerRef = useRef<number | null>(null);

  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: 10000
  });
  const charactersQuery = useQuery({
    queryKey: characterKeys.lists(projectId),
    queryFn: () => fetchCharacters(projectId),
    enabled: projectId.length > 0
  });
  const scenesQuery = useQuery({
    queryKey: sceneKeys.lists(projectId),
    queryFn: () => fetchScenes(projectId),
    enabled: projectId.length > 0
  });
  const shotsQuery = useQuery({
    queryKey: shotKeys.lists(projectId),
    queryFn: () => fetchShots(projectId),
    enabled: projectId.length > 0
  });
  const productionQuery = useQuery({
    queryKey: productionStatusKeys.project(projectId),
    queryFn: () => fetchProjectProductionStatus(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      (query.state.data?.items ?? []).some((shot) =>
        [shot.steps.first_frame?.status, shot.steps.end_frame?.status, shot.steps.video?.status].some(
          (status) => status === "running"
        )
      )
        ? 3000
        : false
  });
  const generationTasksQuery = useQuery({
    queryKey: generationTaskKeys.lists(projectId),
    queryFn: () => fetchGenerationTasks(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      query.state.data?.items.some((task) => task.latest_run_status === "queued" || task.latest_run_status === "running")
        ? 3000
        : false
  });
  const timelineQuery = useQuery({
    queryKey: timelineKeys.timeline(projectId),
    queryFn: () => fetchProjectTimeline(projectId),
    enabled: projectId.length > 0
  });
  const capabilitiesQuery = useQuery({
    queryKey: shotKeys.systemCapabilities(),
    queryFn: fetchSystemCapabilities,
    enabled: projectId.length > 0
  });
  const videoWorkflowsQuery = useQuery({
    queryKey: shotKeys.videoWorkflows(projectId),
    queryFn: () => fetchVideoWorkflows(projectId),
    enabled: projectId.length > 0
  });

  const characters = charactersQuery.data?.items ?? [];
  const scenes = scenesQuery.data?.items ?? [];
  const shots = shotsQuery.data?.items ?? [];
  const generationTasks = generationTasksQuery.data?.items ?? [];
  const productionStatus = productionQuery.data ?? null;
  const timeline = timelineQuery.data ?? null;
  const videoAvailable =
    Boolean(capabilitiesQuery.data?.video_generation?.available) &&
    Boolean(videoWorkflowsQuery.data?.items.some((workflow) => workflow.available));
  const comfyUiAvailable =
    Boolean(capabilitiesQuery.data?.keyframe_generation?.available) ||
    Boolean(capabilitiesQuery.data?.video_generation?.available);
  const adopted = countAdoptedSteps(productionStatus);

  const recommendation = useMemo(
    () =>
      buildStudioRecommendation({
        projectId,
        characterCount: charactersQuery.data?.total ?? 0,
        sceneCount: scenesQuery.data?.total ?? 0,
        shots,
        productionStatus,
        generationTasks,
        videoGenerationAvailable: videoAvailable
      }),
    [
      charactersQuery.data?.total,
      generationTasks,
      productionStatus,
      projectId,
      sceneQueryTotal(scenesQuery.data?.total),
      shots,
      videoAvailable
    ]
  );

  const stages = useMemo(
    () =>
      buildStudioStages({
        characterCount: charactersQuery.data?.total ?? 0,
        sceneCount: scenesQuery.data?.total ?? 0,
        shotCount: shotsQuery.data?.total ?? 0,
        productionStatus,
        timeline
      }),
    [charactersQuery.data?.total, productionStatus, scenesQuery.data?.total, shotsQuery.data?.total, timeline]
  );

  const issues = useMemo(
    () =>
      buildStudioIssues({
        apiAvailable: healthQuery.isSuccess,
        comfyUiAvailable,
        videoAvailable,
        productionStatus,
        generationTasks,
        timeline
      }),
    [comfyUiAvailable, generationTasks, healthQuery.isSuccess, productionStatus, timeline, videoAvailable]
  );

  const recentItems = useMemo(
    () => buildRecentItems({ projectId, characters, scenes, shots, tasks: generationTasks }),
    [characters, generationTasks, projectId, scenes, shots]
  );

  const selectedShot = shots.find((shot) => shot.id === session.selectedShotId) ?? null;
  const selectedProductionShot = findProductionShot(productionStatus, selectedShot?.id ?? null);
  const selectedCharacter =
    session.selectedEntityType === "character"
      ? characters.find((character) => character.id === session.selectedEntityId) ?? null
      : null;
  const selectedScene =
    session.selectedEntityType === "scene"
      ? scenes.find((scene) => scene.id === session.selectedEntityId) ?? null
      : null;

  const updateSession = useCallback(
    (updater: (current: StudioSessionState) => StudioSessionState) => {
      setSession((current) => {
        const next = { ...updater(current), updatedAt: new Date().toISOString() };
        try {
          saveStudioSession(next);
        } catch {
          setLocalNotice("工作现场保存失败，本次会话仍可继续使用。");
        }
        return next;
      });
    },
    []
  );

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    setIsSavingLayout(true);
    if (layoutSaveTimerRef.current) {
      window.clearTimeout(layoutSaveTimerRef.current);
    }
    layoutSaveTimerRef.current = window.setTimeout(() => {
      try {
        saveStudioShellLayout(`studio:${projectId}`, layout);
        setLayoutSaveFailed(false);
      } catch {
        setLayoutSaveFailed(true);
      } finally {
        setIsSavingLayout(false);
      }
    }, 220);
    return () => {
      if (layoutSaveTimerRef.current) {
        window.clearTimeout(layoutSaveTimerRef.current);
      }
    };
  }, [layout, projectId]);

  useEffect(() => {
    const context = parseStudioUrlContext(location.search);
    if (context.ignored) {
      setLocalNotice("已忽略无效的 Studio 上下文参数。");
    }
    updateSession((current) => {
      let next = { ...current, lastRoute: `${location.pathname}${location.search}` };
      if (context.selectedShotId) {
        next = {
          ...next,
          currentMode: context.intent === "generate" ? "workflow" : current.currentMode,
          currentView: context.intent === "generate" ? "shot_console" : current.currentView,
          selectedShotId: context.selectedShotId,
          selectedEntityType: "shot",
          selectedEntityId: context.selectedShotId,
          inspectorTab: context.intent === "generate" ? "next" : "info"
        };
      } else if (context.selectedEntityType && context.selectedEntityId) {
        next = {
          ...next,
          selectedEntityType: context.selectedEntityType,
          selectedEntityId: context.selectedEntityId,
          selectedShotId: null,
          inspectorTab: "info"
        };
      }
      return next;
    });
  }, [location.pathname, location.search, updateSession]);

  useEffect(() => {
    if (!shotsQuery.isSuccess || !charactersQuery.isSuccess || !scenesQuery.isSuccess) {
      return;
    }
    updateSession((current) =>
      sanitizeStudioSessionSelection(current, {
        shotIds: new Set(shots.map((shot) => shot.id)),
        characterIds: new Set(characters.map((character) => character.id)),
        sceneIds: new Set(scenes.map((scene) => scene.id))
      })
    );
  }, [
    characters,
    charactersQuery.isSuccess,
    scenes,
    scenesQuery.isSuccess,
    shots,
    shotsQuery.isSuccess,
    updateSession
  ]);

  const updateLayout = useCallback((updater: (current: StudioShellLayoutState) => StudioShellLayoutState) => {
    setLayout((current) => updater(current));
  }, []);

  const resetLayout = useCallback(() => {
    setLayout(createDefaultStudioShellLayout());
    setToast("布局已恢复默认。");
  }, []);

  const clearSession = useCallback(() => {
    clearStudioSession(projectId);
    setSession(createDefaultStudioSession(projectId));
    setToast("工作现场已清除。");
  }, [projectId]);

  const selectShot = useCallback(
    (shotId: string, view: StudioView = "shot_console") => {
      updateSession((current) => ({
        ...current,
        currentMode: view === "storyboard" ? "storyboard" : "workflow",
        currentView: view,
        selectedShotId: shotId,
        selectedEntityType: "shot",
        selectedEntityId: shotId,
        inspectorTab: "info"
      }));
    },
    [updateSession]
  );

  const selectEntity = useCallback(
    (type: Exclude<StudioContextEntityType, null>, entityId: string) => {
      updateSession((current) => ({
        ...current,
        selectedEntityType: type,
        selectedEntityId: entityId,
        selectedShotId: type === "shot" ? entityId : null,
        inspectorTab: "info"
      }));
    },
    [updateSession]
  );

  const setView = useCallback(
    (view: StudioView) => {
      updateSession((current) => ({
        ...current,
        currentView: view,
        currentMode: view === "storyboard" ? "storyboard" : view === "workflow" ? "workflow" : "start"
      }));
    },
    [updateSession]
  );

  const startResize = useCallback(
    (panel: ResizablePanel) => (event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      const startValue =
        panel === "left"
          ? layout.leftWidth
          : panel === "right"
            ? layout.rightWidth
            : layout.bottomHeight;
      dragSessionRef.current = { panel, startX: event.clientX, startY: event.clientY, startValue };
      setIsResizing(true);
      event.currentTarget.setPointerCapture?.(event.pointerId);
    },
    [layout.bottomHeight, layout.leftWidth, layout.rightWidth]
  );

  const resetPanel = useCallback(
    (panel: ResizablePanel) => {
      updateLayout((current) => ({
        ...current,
        leftWidth: panel === "left" ? STUDIO_SHELL_DEFAULTS.leftWidth : current.leftWidth,
        rightWidth: panel === "right" ? STUDIO_SHELL_DEFAULTS.rightWidth : current.rightWidth,
        bottomHeight: panel === "bottom" ? STUDIO_SHELL_DEFAULTS.bottomHeight : current.bottomHeight
      }));
    },
    [updateLayout]
  );

  const clampPanelResize = useCallback(
    (current: StudioShellLayoutState, panel: "left" | "right", requestedWidth: number) => {
      const navWidthForLayout =
        current.navCollapsed || viewportWidth < 768
          ? STUDIO_SHELL_LIMITS.navCollapsed
          : STUDIO_SHELL_LIMITS.navExpanded;
      const centerMinimumWidth = viewportWidth >= 1440 ? 560 : 360;
      const otherWidth =
        panel === "left"
          ? current.rightPanelCollapsed || current.focusMode
            ? 0
            : current.rightWidth
          : current.leftPanelCollapsed || current.focusMode
            ? 0
            : current.leftWidth;
      const dynamicMax = viewportWidth - navWidthForLayout - otherWidth - centerMinimumWidth - 8;
      const min = panel === "left" ? STUDIO_SHELL_LIMITS.leftMin : STUDIO_SHELL_LIMITS.rightMin;
      const max = panel === "left" ? STUDIO_SHELL_LIMITS.leftMax : STUDIO_SHELL_LIMITS.rightMax;
      return clamp(requestedWidth, min, Math.min(max, Math.max(min, dynamicMax)));
    },
    [viewportWidth]
  );

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      const sessionRef = dragSessionRef.current;
      if (!sessionRef) return;
      updateLayout((current) => {
        if (sessionRef.panel === "left") {
          return {
            ...current,
            leftPanelCollapsed: false,
            leftWidth: clampPanelResize(current, "left", sessionRef.startValue + event.clientX - sessionRef.startX)
          };
        }
        if (sessionRef.panel === "right") {
          return {
            ...current,
            rightPanelCollapsed: false,
            rightWidth: clampPanelResize(current, "right", sessionRef.startValue - (event.clientX - sessionRef.startX))
          };
        }
        return {
          ...current,
          bottomExpanded: true,
          bottomHeight: clamp(
            sessionRef.startValue - (event.clientY - sessionRef.startY),
            STUDIO_SHELL_LIMITS.bottomMin,
            STUDIO_SHELL_LIMITS.bottomMax
          )
        };
      });
    };
    const clearResize = () => {
      dragSessionRef.current = null;
      setIsResizing(false);
    };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", clearResize);
    window.addEventListener("pointercancel", clearResize);
    window.addEventListener("blur", clearResize);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", clearResize);
      window.removeEventListener("pointercancel", clearResize);
      window.removeEventListener("blur", clearResize);
      clearResize();
    };
  }, [clampPanelResize, updateLayout]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab" || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      updateLayout((current) => ({ ...current, focusMode: !current.focusMode }));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [updateLayout]);

  const compactMode = viewportWidth < 1200;
  const navWidth =
    layout.navCollapsed || viewportWidth < 768 ? STUDIO_SHELL_LIMITS.navCollapsed : STUDIO_SHELL_LIMITS.navExpanded;
  const leftWidth = compactMode ? 0 : getPanelWidth(layout, "left");
  const rightWidth = compactMode ? 0 : getPanelWidth(layout, "right");
  const bottomHeight =
    layout.focusMode || !layout.bottomExpanded ? STUDIO_SHELL_LIMITS.bottomCollapsed : layout.bottomHeight;
  const showLeftPanel = isPanelVisible(leftWidth);
  const showRightPanel = isPanelVisible(rightWidth);
  const bottomExpanded = !layout.focusMode && layout.bottomExpanded;

  if (projectQuery.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--studio-color-page)] p-6 text-[var(--studio-color-text)]">
        <section className="max-w-md rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-6">
          <h1 className="text-lg font-semibold">项目不存在或已被删除</h1>
          <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">请返回项目列表重新选择一个项目。</p>
          <Button asChild className="mt-5">
            <Link to="/projects">返回项目列表</Link>
          </Button>
        </section>
      </div>
    );
  }

  return (
    <div className="h-screen min-h-[640px] overflow-hidden bg-[var(--studio-color-page)] text-[var(--studio-color-text)]" data-testid="studio-workspace-page">
      <div className="flex h-full min-w-0 flex-col">
        <StudioProjectHeader
          project={projectQuery.data ?? null}
          navCollapsed={layout.navCollapsed}
          apiConnected={healthQuery.isSuccess}
          comfyUiAvailable={comfyUiAvailable}
          layoutSaveFailed={layoutSaveFailed}
          isSavingLayout={isSavingLayout}
          onToggleNav={() => updateLayout((current) => ({ ...current, navCollapsed: !current.navCollapsed }))}
          onResetLayout={resetLayout}
          onClearSession={clearSession}
        />

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <StudioGlobalNavigation
            projectId={projectId}
            width={navWidth}
            navCollapsed={layout.navCollapsed}
          />

          {showLeftPanel ? (
            <StudioContextPanel
              width={leftWidth}
              activeTab={session.leftPanelTab}
              project={projectQuery.data ?? null}
              recommendation={recommendation}
              stages={stages}
              shots={shots}
              characters={characters}
              scenes={scenes}
              selectedShotId={session.selectedShotId}
              selectedEntityType={session.selectedEntityType}
              selectedEntityId={session.selectedEntityId}
              loading={projectQuery.isLoading || charactersQuery.isLoading || scenesQuery.isLoading || shotsQuery.isLoading}
              onActiveTabChange={(tab) => updateSession((current) => ({ ...current, leftPanelTab: tab }))}
              onSelectShot={selectShot}
              onSelectEntity={selectEntity}
              onCollapse={() => updateLayout((current) => ({ ...current, leftPanelCollapsed: true }))}
            />
          ) : null}

          <PanelDivider
            hidden={layout.focusMode || compactMode}
            testId="studio-left-resizer"
            label="调整左侧上下文面板宽度"
            onPointerDown={startResize("left")}
            onDoubleClick={() => resetPanel("left")}
          />

          <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[var(--studio-color-workspace)]">
            <div className="flex h-10 shrink-0 items-center justify-between border-b border-[var(--studio-color-border)] px-4">
              <div className="flex min-w-0 items-center gap-2">
                {viewTabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    aria-pressed={session.currentView === tab.id}
                    className={cn(
                      "rounded-[var(--studio-radius-button)] px-3 py-1.5 text-sm transition",
                      session.currentView === tab.id
                        ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]"
                        : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
                    )}
                    onClick={() => setView(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {compactMode ? (
                  <>
                    <Button type="button" size="sm" variant="secondary" onClick={() => setCompactDrawer("left")}>
                      上下文
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={() => setCompactDrawer("right")}>
                      Inspector
                    </Button>
                  </>
                ) : null}
                {!showLeftPanel && !layout.focusMode && !compactMode ? (
                  <Button type="button" size="sm" variant="secondary" onClick={() => updateLayout((current) => ({ ...current, leftPanelCollapsed: false }))}>
                    展开左栏
                  </Button>
                ) : null}
                {!showRightPanel && !layout.focusMode && !compactMode ? (
                  <Button type="button" size="sm" variant="secondary" onClick={() => updateLayout((current) => ({ ...current, rightPanelCollapsed: false }))}>
                    展开 Inspector
                  </Button>
                ) : null}
                <Button type="button" size="sm" variant="secondary" onClick={resetLayout}>
                  <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                  恢复默认布局
                </Button>
                <Button type="button" size="sm" variant={layout.focusMode ? "default" : "secondary"} onClick={() => updateLayout((current) => ({ ...current, focusMode: !current.focusMode }))}>
                  {layout.focusMode ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  {layout.focusMode ? "退出专注" : "专注模式"}
                </Button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto">
              <StudioCenter
                projectId={projectId}
                view={session.currentView}
                project={projectQuery.data ?? null}
                recommendation={recommendation}
                charactersTotal={charactersQuery.data?.total ?? 0}
                scenesTotal={scenesQuery.data?.total ?? 0}
                shots={shots}
                stages={stages}
                recentItems={recentItems}
                selectedShot={selectedShot}
                selectedProductionShot={selectedProductionShot}
                adopted={adopted}
                loading={projectQuery.isLoading || shotsQuery.isLoading || productionQuery.isLoading}
                partialErrors={{
                  characters: charactersQuery.isError,
                  scenes: scenesQuery.isError,
                  shots: shotsQuery.isError,
                  generation: generationTasksQuery.isError,
                  production: productionQuery.isError
                }}
                onPrimaryAction={() => navigate(recommendation.href)}
                onSetView={setView}
                onSelectShot={selectShot}
              />
            </div>

            <PanelDivider
              horizontal
              hidden={layout.focusMode}
              testId="studio-bottom-resizer"
              label="调整底部工作区高度"
              onPointerDown={startResize("bottom")}
              onDoubleClick={() => resetPanel("bottom")}
            />
            <StudioBottomWorkspace
              height={bottomHeight}
              expanded={bottomExpanded}
              activeTab={session.bottomPanelTab}
              tasks={generationTasks}
              issues={issues}
              onToggleExpanded={() => updateLayout((current) => ({ ...current, bottomExpanded: !current.bottomExpanded }))}
              onTabChange={(tab) => updateSession((current) => ({ ...current, bottomPanelTab: tab }))}
            />
          </main>

          <PanelDivider
            hidden={layout.focusMode || compactMode}
            testId="studio-right-resizer"
            label="调整右侧 Inspector 宽度"
            onPointerDown={startResize("right")}
            onDoubleClick={() => resetPanel("right")}
          />

          {showRightPanel ? (
            <StudioInspectorPanel
              width={rightWidth}
              projectId={projectId}
              activeTab={session.inspectorTab}
              recommendation={recommendation}
              selectedShot={selectedShot}
              selectedProductionShot={selectedProductionShot}
              selectedCharacter={selectedCharacter}
              selectedScene={selectedScene}
              issues={issues}
              onActiveTabChange={(tab) => updateSession((current) => ({ ...current, inspectorTab: tab }))}
              onCollapse={() => updateLayout((current) => ({ ...current, rightPanelCollapsed: true }))}
              onNavigate={navigate}
            />
          ) : null}
        </div>
      </div>

      {compactMode && compactDrawer ? (
        <CompactDrawer title={compactDrawer === "left" ? "上下文" : "Inspector"} onClose={() => setCompactDrawer(null)}>
          {compactDrawer === "left" ? (
            <StudioContextPanel
              width={Math.min(420, viewportWidth - 48)}
              activeTab={session.leftPanelTab}
              project={projectQuery.data ?? null}
              recommendation={recommendation}
              stages={stages}
              shots={shots}
              characters={characters}
              scenes={scenes}
              selectedShotId={session.selectedShotId}
              selectedEntityType={session.selectedEntityType}
              selectedEntityId={session.selectedEntityId}
              loading={projectQuery.isLoading || shotsQuery.isLoading}
              embedded
              onActiveTabChange={(tab) => updateSession((current) => ({ ...current, leftPanelTab: tab }))}
              onSelectShot={(shotId) => {
                selectShot(shotId);
                setCompactDrawer(null);
              }}
              onSelectEntity={(type, entityId) => {
                selectEntity(type, entityId);
                setCompactDrawer(null);
              }}
              onCollapse={() => setCompactDrawer(null)}
            />
          ) : (
            <StudioInspectorPanel
              width={Math.min(420, viewportWidth - 48)}
              projectId={projectId}
              activeTab={session.inspectorTab}
              recommendation={recommendation}
              selectedShot={selectedShot}
              selectedProductionShot={selectedProductionShot}
              selectedCharacter={selectedCharacter}
              selectedScene={selectedScene}
              issues={issues}
              embedded
              onActiveTabChange={(tab) => updateSession((current) => ({ ...current, inspectorTab: tab }))}
              onCollapse={() => setCompactDrawer(null)}
              onNavigate={navigate}
            />
          )}
        </CompactDrawer>
      ) : null}

      {isResizing ? <div className="fixed inset-0 z-[var(--studio-z-resize)] cursor-grabbing" data-testid="studio-formal-resize-shield" /> : null}
      {[localNotice, toast].filter(Boolean).map((message) => (
        <div
          key={message}
          className="fixed right-4 top-16 z-[var(--studio-z-toast)] max-w-sm rounded-[var(--studio-radius-floating)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] px-4 py-3 text-sm shadow-xl"
          role="status"
        >
          {message}
          <button type="button" aria-label="关闭提示" className="ml-3 text-[var(--studio-color-text-muted)]" onClick={() => {
            if (message === localNotice) setLocalNotice(null);
            if (message === toast) setToast(null);
          }}>
            <X className="inline h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

function sceneQueryTotal(value: number | undefined) {
  return value ?? 0;
}

function StudioProjectHeader({
  project,
  navCollapsed,
  apiConnected,
  comfyUiAvailable,
  layoutSaveFailed,
  isSavingLayout,
  onToggleNav,
  onResetLayout,
  onClearSession
}: {
  project: Project | null;
  navCollapsed: boolean;
  apiConnected: boolean;
  comfyUiAvailable: boolean;
  layoutSaveFailed: boolean;
  isSavingLayout: boolean;
  onToggleNav: () => void;
  onResetLayout: () => void;
  onClearSession: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--studio-color-border)] bg-[var(--studio-color-workspace)] px-3">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          aria-expanded={!navCollapsed}
          aria-label={navCollapsed ? "展开全局导航" : "折叠全局导航"}
          className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--studio-radius-button)] text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)]"
          onClick={onToggleNav}
        >
          <Menu className="h-4 w-4" />
        </button>
        <Link to="/projects" className="grid h-8 w-8 place-items-center rounded-[var(--studio-radius-button)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]">
          <FolderKanban className="h-4 w-4 text-[var(--studio-color-primary)]" />
        </Link>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{project?.name ?? "正在加载项目"}</div>
          <div className="truncate text-xs text-[var(--studio-color-text-muted)]">Studio 创作工作台</div>
        </div>
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <StudioStatusBadge tone={layoutSaveFailed ? "danger" : isSavingLayout ? "warning" : "success"}>
          {layoutSaveFailed ? "布局保存失败" : isSavingLayout ? "正在保存" : "已保存"}
        </StudioStatusBadge>
        <StudioStatusBadge tone={apiConnected ? "success" : "danger"}>
          {apiConnected ? "后端已连接" : "后端不可用"}
        </StudioStatusBadge>
        <StudioStatusBadge tone={comfyUiAvailable ? "success" : "warning"}>
          {comfyUiAvailable ? "ComfyUI 可用" : "ComfyUI 待检查"}
        </StudioStatusBadge>
        <Button type="button" size="sm" variant="secondary" onClick={onResetLayout}>
          恢复默认布局
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={onClearSession}>
          清除工作现场
        </Button>
      </div>
    </header>
  );
}

function StudioGlobalNavigation({
  projectId,
  width,
  navCollapsed
}: {
  projectId: string;
  width: number;
  navCollapsed: boolean;
}) {
  return (
    <aside className="flex shrink-0 flex-col border-r border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] transition-[width] duration-[var(--studio-motion-panel)]" style={{ width }} data-testid="studio-formal-global-nav">
      <nav className="space-y-1 p-2" aria-label="Studio 项目导航">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.id}
              to={item.href(projectId)}
              className="flex h-10 w-full items-center gap-3 rounded-[var(--studio-radius-button)] px-3 text-sm text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)]"
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={cn("truncate", navCollapsed && "sr-only")}>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

function PanelDivider({
  horizontal = false,
  hidden,
  testId,
  label,
  onPointerDown,
  onDoubleClick
}: {
  horizontal?: boolean;
  hidden: boolean;
  testId: string;
  label: string;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onDoubleClick: () => void;
}) {
  return (
    <div
      aria-label={label}
      role="separator"
      tabIndex={0}
      data-testid={testId}
      className={cn(
        "z-[var(--studio-z-panel)] shrink-0 bg-transparent hover:bg-[var(--studio-color-primary)]/50",
        horizontal ? "h-1 cursor-row-resize" : "w-1 cursor-col-resize",
        hidden && "hidden"
      )}
      onPointerDown={onPointerDown}
      onDoubleClick={onDoubleClick}
    />
  );
}

function StudioContextPanel({
  width,
  activeTab,
  project,
  recommendation,
  stages,
  shots,
  characters,
  scenes,
  selectedShotId,
  selectedEntityType,
  selectedEntityId,
  loading,
  embedded = false,
  onActiveTabChange,
  onSelectShot,
  onSelectEntity,
  onCollapse
}: {
  width: number;
  activeTab: StudioContextTab;
  project: Project | null;
  recommendation: StudioRecommendation;
  stages: StudioStage[];
  shots: Shot[];
  characters: Character[];
  scenes: Scene[];
  selectedShotId: string | null;
  selectedEntityType: StudioContextEntityType;
  selectedEntityId: string | null;
  loading: boolean;
  embedded?: boolean;
  onActiveTabChange: (tab: StudioContextTab) => void;
  onSelectShot: (shotId: string) => void;
  onSelectEntity: (type: Exclude<StudioContextEntityType, null>, entityId: string) => void;
  onCollapse: () => void;
}) {
  const Wrapper = embedded ? "div" : "aside";
  return (
    <Wrapper className={cn("min-w-0 shrink-0 border-r border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]", embedded && "h-full border-r-0")} style={{ width }} data-testid="studio-formal-left-panel">
      <div className="flex h-11 items-center justify-between border-b border-[var(--studio-color-border)] px-3">
        <div>
          <div className="text-xs font-semibold text-[#cfd2ff]">上下文面板</div>
          <div className="text-[11px] text-[var(--studio-color-text-muted)]">{project?.name ?? "项目加载中"}</div>
        </div>
        <button type="button" aria-label="折叠上下文面板" className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]" onClick={onCollapse}>
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>
      <div className="flex h-[calc(100%-44px)] min-h-0 flex-col">
        <TabButtons tabs={contextTabs} activeTab={activeTab} onChange={onActiveTabChange} />
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {loading ? <Skeleton className="h-72" /> : null}
          {!loading && activeTab === "overview" ? (
            <div className="space-y-4">
              <MiniPanel title="推荐下一步">
                <p className="text-sm font-semibold">{recommendation.title}</p>
                <p className="mt-2 text-xs leading-5 text-[var(--studio-color-text-muted)]">{recommendation.reason}</p>
                <Button asChild size="sm" className="mt-3">
                  <Link to={recommendation.href}>执行建议</Link>
                </Button>
              </MiniPanel>
              <MiniPanel title="制作阶段">
                <div className="space-y-2">
                  {stages.map((stage) => (
                    <div key={stage.key} className="flex items-center justify-between gap-3 rounded-[var(--studio-radius-card)] bg-[var(--studio-color-surface)] px-3 py-2">
                      <span className="text-sm">{stage.title}</span>
                      <StudioStatusBadge tone={stage.status === "completed" ? "success" : stage.status === "blocked" ? "danger" : stage.status === "current" ? "warning" : "draft"}>{stageLabel(stage.status)}</StudioStatusBadge>
                    </div>
                  ))}
                </div>
              </MiniPanel>
            </div>
          ) : null}
          {!loading && activeTab === "shots" ? (
            <div className="space-y-2">
              {shots.length === 0 ? <InlineEmpty title="暂无镜头" detail="创建第一个镜头后，这里会显示真实镜头列表。" /> : null}
              {shots.map((shot) => (
                <button
                  key={shot.id}
                  type="button"
                  className={cn("w-full rounded-[var(--studio-radius-card)] border p-3 text-left transition hover:border-[var(--studio-color-primary)]", selectedShotId === shot.id ? "border-[var(--studio-color-primary)] bg-[var(--studio-color-primary-soft)]" : "border-[var(--studio-color-border)] bg-[var(--studio-color-surface)]")}
                  onClick={() => onSelectShot(shot.id)}
                >
                  <div className="text-xs text-[var(--studio-color-text-muted)]">#{shot.order_index}</div>
                  <div className="mt-1 truncate text-sm font-semibold">{shot.name}</div>
                  <div className="mt-2 text-xs text-[var(--studio-color-text-muted)]">{shot.character_count} 人物 / {shot.reference_count} 参考图</div>
                </button>
              ))}
            </div>
          ) : null}
          {!loading && activeTab === "assets" ? (
            <div className="space-y-4">
              <AssetGroup title="角色" empty="请先创建角色">
                {characters.map((character) => (
                  <AssetButton key={character.id} active={selectedEntityType === "character" && selectedEntityId === character.id} label={character.name} detail={`${character.look_count} 造型 / ${character.reference_count} 参考图`} onClick={() => onSelectEntity("character", character.id)} />
                ))}
              </AssetGroup>
              <AssetGroup title="场景" empty="请先创建场景">
                {scenes.map((scene) => (
                  <AssetButton key={scene.id} active={selectedEntityType === "scene" && selectedEntityId === scene.id} label={scene.name} detail={`${scene.state_count} 状态 / ${scene.reference_count} 参考图`} onClick={() => onSelectEntity("scene", scene.id)} />
                ))}
              </AssetGroup>
            </div>
          ) : null}
        </div>
      </div>
    </Wrapper>
  );
}

function StudioCenter({
  projectId,
  view,
  project,
  recommendation,
  charactersTotal,
  scenesTotal,
  shots,
  stages,
  recentItems,
  selectedShot,
  selectedProductionShot,
  adopted,
  loading,
  partialErrors,
  onPrimaryAction,
  onSetView,
  onSelectShot
}: {
  projectId: string;
  view: StudioView;
  project: Project | null;
  recommendation: StudioRecommendation;
  charactersTotal: number;
  scenesTotal: number;
  shots: Shot[];
  stages: StudioStage[];
  recentItems: StudioRecentItem[];
  selectedShot: Shot | null;
  selectedProductionShot: ShotProductionStatus | null;
  adopted: { firstFrame: number; endFrame: number; video: number };
  loading: boolean;
  partialErrors: Record<string, boolean>;
  onPrimaryAction: () => void;
  onSetView: (view: StudioView) => void;
  onSelectShot: (shotId: string, view?: StudioView) => void;
}) {
  if (loading) {
    return <div className="mx-auto grid w-full max-w-5xl gap-4 p-8"><Skeleton className="h-48" /><Skeleton className="h-64" /></div>;
  }

  if (view === "storyboard") {
    return <StoryboardView projectId={projectId} shots={shots} onSelectShot={(shotId) => onSelectShot(shotId, "storyboard")} />;
  }

  if (view === "workflow") {
    return <WorkflowBridgeView projectId={projectId} onSetView={onSetView} />;
  }

  if (view === "shot_console") {
    return <ShotConsolePreview projectId={projectId} shot={selectedShot} productionShot={selectedProductionShot} />;
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-[960px] flex-col justify-center p-8">
      <div className="text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-[var(--studio-radius-floating)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]">
          <Sparkles className="h-7 w-7 text-[var(--studio-color-primary)]" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold">{project?.name ?? "Local Drama Studio"}</h1>
        <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">根据当前项目状态，Studio 会把最值得继续的动作放到你面前。</p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Button type="button" onClick={onPrimaryAction}>{recommendation.title}</Button>
          <Button asChild type="button" variant="secondary"><Link to={`/projects/${projectId}/canvas?view=storyboard`}>打开现有故事板工作区</Link></Button>
          <Button asChild type="button" variant="secondary"><Link to={`/projects/${projectId}/canvas?view=workflow`}>打开现有工作流画布</Link></Button>
        </div>
        <p className="mt-3 text-xs text-[var(--studio-color-text-muted)]">{recommendation.reason}</p>
      </div>

      {Object.values(partialErrors).some(Boolean) ? (
        <StatusMessage tone="neutral">部分数据加载失败，已加载区域仍可继续使用。</StatusMessage>
      ) : null}

      <section className="mt-8 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="角色" value={charactersTotal} />
        <Metric label="场景" value={scenesTotal} />
        <Metric label="镜头" value={shots.length} />
        <Metric label="首帧采用" value={adopted.firstFrame} />
        <Metric label="尾帧采用" value={adopted.endFrame} />
        <Metric label="视频采用" value={adopted.video} />
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <StudioCard title="制作进度">
          <div className="space-y-3">
            {stages.map((stage) => (
              <div key={stage.key} className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold">{stage.title}</span>
                  <StudioStatusBadge tone={stage.status === "completed" ? "success" : stage.status === "blocked" ? "danger" : stage.status === "current" ? "warning" : "draft"}>{stageLabel(stage.status)}</StudioStatusBadge>
                </div>
                <p className="mt-1 text-xs text-[var(--studio-color-text-muted)]">{stage.detail}</p>
              </div>
            ))}
          </div>
        </StudioCard>
        <StudioCard title="最近继续">
          {recentItems.length === 0 ? <InlineEmpty title="暂无最近记录" detail="真实创建角色、场景、镜头或任务后会出现在这里。" /> : null}
          <div className="space-y-2">
            {recentItems.map((item) => (
              <Link key={item.id} to={item.href} className="block rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3 hover:border-[var(--studio-color-primary)]">
                <div className="text-xs text-[var(--studio-color-text-muted)]">{item.label}</div>
                <div className="mt-1 truncate text-sm font-semibold">{item.title}</div>
              </Link>
            ))}
          </div>
        </StudioCard>
      </section>

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <QuickEntry title="角色与造型" detail={`${charactersTotal} 个角色`} href={`/projects/${projectId}/characters`} />
        <QuickEntry title="场景与状态" detail={`${scenesTotal} 个场景`} href={`/projects/${projectId}/scenes`} />
        <QuickEntry title="镜头列表" detail={`${shots.length} 个镜头`} href={`/projects/${projectId}/shots`} />
        <QuickEntry title="生成任务" detail="查看关键帧与视频任务" href={`/projects/${projectId}/generation`} />
      </section>
    </div>
  );
}

function StoryboardView({ projectId, shots, onSelectShot }: { projectId: string; shots: Shot[]; onSelectShot: (shotId: string) => void }) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">故事板</h1>
          <p className="mt-1 text-sm text-[var(--studio-color-text-muted)]">第一版使用项目现有镜头顺序展示，不做复杂剪辑。</p>
        </div>
        <Button asChild variant="secondary"><Link to={`/projects/${projectId}/canvas?view=storyboard`}>打开现有故事板工作区</Link></Button>
      </div>
      {shots.length === 0 ? <div className="mt-8"><InlineEmpty title="暂无镜头" detail="请先创建镜头。" /></div> : null}
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {shots.map((shot) => (
          <button key={shot.id} type="button" className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4 text-left hover:border-[var(--studio-color-primary)]" onClick={() => onSelectShot(shot.id)}>
            <div className="aspect-video rounded-[var(--studio-radius-card)] border border-dashed border-[var(--studio-color-border-strong)] bg-[var(--studio-color-page)]" />
            <div className="mt-3 text-xs text-[var(--studio-color-text-muted)]">镜头 {shot.order_index}</div>
            <h2 className="mt-1 truncate text-sm font-semibold">{shot.name}</h2>
            <p className="mt-2 text-xs text-[var(--studio-color-text-muted)]">{shot.duration_seconds ?? "-"} 秒 / {shot.character_count} 人物 / {shot.scene?.name ?? "未选场景"}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function WorkflowBridgeView({ projectId, onSetView }: { projectId: string; onSetView: (view: StudioView) => void }) {
  return (
    <div className="grid min-h-full place-items-center p-8">
      <section className="max-w-xl text-center">
        <LayoutDashboard className="mx-auto h-12 w-12 text-[var(--studio-color-primary)]" />
        <h1 className="mt-4 text-xl font-semibold">工作流画布入口</h1>
        <p className="mt-2 text-sm leading-6 text-[var(--studio-color-text-muted)]">正式 Studio 入口先承接工作现场与下一步建议，完整 Canvas 2.0 将在后续 Sprint 演进。现有画布工作区继续可用。</p>
        <div className="mt-5 flex justify-center gap-2">
          <Button asChild><Link to={`/projects/${projectId}/canvas?view=workflow`}>打开现有工作流画布</Link></Button>
          <Button type="button" variant="secondary" onClick={() => onSetView("start")}>返回续作起点</Button>
        </div>
      </section>
    </div>
  );
}

function ShotConsolePreview({ projectId, shot, productionShot }: { projectId: string; shot: Shot | null; productionShot: ShotProductionStatus | null }) {
  if (!shot) {
    return <div className="grid min-h-full place-items-center p-8"><InlineEmpty title="请选择一个镜头" detail="从左侧镜头列表选择后，这里会显示镜头节点的详细编辑入口。" /></div>;
  }
  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs text-[var(--studio-color-text-muted)]">镜头 {shot.order_index}</div>
          <h1 className="mt-1 text-xl font-semibold">{shot.name}</h1>
          <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">{shot.visual_description || shot.story_description || "暂无画面描述。"}</p>
        </div>
        <Button asChild><Link to={`/projects/${projectId}/shots/${shot.id}`}>打开镜头详细工作台</Link></Button>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <ProductionTile title="首帧" status={productionShot?.steps.first_frame?.status} />
        <ProductionTile title="尾帧" status={productionShot?.steps.end_frame?.status} />
        <ProductionTile title="视频" status={productionShot?.steps.video?.status} />
      </div>
      <StudioCard title="镜头生成控制台说明">
        <p className="text-sm leading-6 text-[var(--studio-color-text-muted)]">Sprint 27B 只把 Sprint 23/26 的镜头快速生成工作台作为 Shot Inspector 的正式入口，不在这里重新实现生成表单。</p>
      </StudioCard>
    </div>
  );
}

function StudioInspectorPanel({
  width,
  projectId,
  activeTab,
  recommendation,
  selectedShot,
  selectedProductionShot,
  selectedCharacter,
  selectedScene,
  issues,
  embedded = false,
  onActiveTabChange,
  onCollapse,
  onNavigate
}: {
  width: number;
  projectId: string;
  activeTab: StudioInspectorTab;
  recommendation: StudioRecommendation;
  selectedShot: Shot | null;
  selectedProductionShot: ShotProductionStatus | null;
  selectedCharacter: Character | null;
  selectedScene: Scene | null;
  issues: StudioIssue[];
  embedded?: boolean;
  onActiveTabChange: (tab: StudioInspectorTab) => void;
  onCollapse: () => void;
  onNavigate: (href: string) => void;
}) {
  const Wrapper = embedded ? "div" : "aside";
  return (
    <Wrapper className={cn("min-w-0 shrink-0 border-l border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]", embedded && "h-full border-l-0")} style={{ width }} data-testid="studio-formal-right-panel">
      <div className="flex h-11 items-center justify-between border-b border-[var(--studio-color-border)] px-3">
        <div>
          <div className="text-xs font-semibold text-[#cfd2ff]">Inspector</div>
          <div className="text-[11px] text-[var(--studio-color-text-muted)]">信息与下一步</div>
        </div>
        <button type="button" aria-label="折叠 Inspector" className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]" onClick={onCollapse}>
          <PanelRightClose className="h-4 w-4" />
        </button>
      </div>
      <div className="flex h-[calc(100%-44px)] min-h-0 flex-col">
        <TabButtons tabs={inspectorTabs} activeTab={activeTab} onChange={onActiveTabChange} />
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {activeTab === "next" ? (
            <div className="space-y-4">
              <StudioCard title="推荐下一步">
                <h2 className="text-base font-semibold">{recommendation.title}</h2>
                <p className="mt-2 text-sm leading-6 text-[var(--studio-color-text-muted)]">{recommendation.reason}</p>
                <Button type="button" className="mt-4" onClick={() => onNavigate(recommendation.href)}>执行建议</Button>
              </StudioCard>
              <StudioCard title="当前问题">
                {issues.length === 0 ? <InlineEmpty title="暂无阻塞" detail="当前没有可识别的生产阻塞。" /> : issues.slice(0, 4).map((issue) => <IssueRow key={issue.key} issue={issue} />)}
              </StudioCard>
            </div>
          ) : null}
          {activeTab === "info" ? (
            <InspectorInfo
              projectId={projectId}
              shot={selectedShot}
              productionShot={selectedProductionShot}
              character={selectedCharacter}
              scene={selectedScene}
            />
          ) : null}
        </div>
      </div>
    </Wrapper>
  );
}

function InspectorInfo({
  projectId,
  shot,
  productionShot,
  character,
  scene
}: {
  projectId: string;
  shot: Shot | null;
  productionShot: ShotProductionStatus | null;
  character: Character | null;
  scene: Scene | null;
}) {
  if (shot) {
    return (
      <StudioCard title="镜头摘要">
        <h2 className="text-base font-semibold">{shot.name}</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <InfoRow label="人物" value={`${shot.character_count} 个`} />
          <InfoRow label="场景" value={shot.scene?.name ?? "未选择"} />
          <InfoRow label="参考图" value={`${shot.reference_count} 张`} />
          <InfoRow label="首帧" value={productionLabel(productionShot?.steps.first_frame?.status)} />
          <InfoRow label="尾帧" value={productionLabel(productionShot?.steps.end_frame?.status)} />
          <InfoRow label="视频" value={productionLabel(productionShot?.steps.video?.status)} />
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm"><Link to={`/projects/${projectId}/shots/${shot.id}`}>打开镜头</Link></Button>
          <Button asChild size="sm" variant="secondary"><Link to={`/projects/${projectId}/canvas?shotId=${shot.id}`}>打开现有画布</Link></Button>
        </div>
      </StudioCard>
    );
  }
  if (character) {
    return (
      <StudioCard title="角色摘要">
        <h2 className="text-base font-semibold">{character.name}</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <InfoRow label="默认造型" value={character.default_look?.name ?? "暂无"} />
          <InfoRow label="造型" value={`${character.look_count} 套`} />
          <InfoRow label="参考图" value={`${character.reference_count} 张`} />
        </dl>
        <Button asChild size="sm" className="mt-4"><Link to={`/projects/${projectId}/characters/${character.id}`}>打开角色详情</Link></Button>
      </StudioCard>
    );
  }
  if (scene) {
    return (
      <StudioCard title="场景摘要">
        <h2 className="text-base font-semibold">{scene.name}</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <InfoRow label="默认状态" value={scene.default_state?.name ?? "暂无"} />
          <InfoRow label="状态" value={`${scene.state_count} 个`} />
          <InfoRow label="参考图" value={`${scene.reference_count} 张`} />
        </dl>
        <Button asChild size="sm" className="mt-4"><Link to={`/projects/${projectId}/scenes/${scene.id}`}>打开场景详情</Link></Button>
      </StudioCard>
    );
  }
  return <InlineEmpty title="请选择内容" detail="选择镜头、角色或场景后，这里会显示摘要和操作入口。" />;
}

function StudioBottomWorkspace({
  height,
  expanded,
  activeTab,
  tasks,
  issues,
  onToggleExpanded,
  onTabChange
}: {
  height: number;
  expanded: boolean;
  activeTab: StudioBottomTab;
  tasks: GenerationTaskSummary[];
  issues: StudioIssue[];
  onToggleExpanded: () => void;
  onTabChange: (tab: StudioBottomTab) => void;
}) {
  const runningTasks = tasks.filter((task) => task.latest_run_status === "queued" || task.latest_run_status === "running");
  return (
    <section className="shrink-0 border-t border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]" style={{ height }} data-testid="studio-formal-bottom-panel">
      <div className="flex h-9 items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <button type="button" aria-label={expanded ? "折叠底部工作区" : "展开底部工作区"} className="rounded-[var(--studio-radius-button)] p-1.5 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]" onClick={onToggleExpanded}>
            <PanelBottomOpen className="h-4 w-4" />
          </button>
          {bottomTabs.map((tab) => (
            <button key={tab.id} type="button" aria-pressed={activeTab === tab.id} className={cn("rounded px-3 py-1 text-xs", activeTab === tab.id ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]" : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]")} onClick={() => onTabChange(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-[var(--studio-color-text-muted)]">运行中 {runningTasks.length} / 问题 {issues.length}</span>
      </div>
      {expanded ? (
        <div className="h-[calc(100%-36px)] overflow-y-auto px-4 pb-4">
          {activeTab === "running" ? (
            runningTasks.length === 0 ? <InlineEmpty title="暂无运行任务" detail="项目当前没有排队中或生成中的任务。" /> : runningTasks.map((task) => <TaskRow key={task.task_id} task={task} />)
          ) : null}
          {activeTab === "issues" ? (
            issues.length === 0 ? <InlineEmpty title="暂无问题" detail="没有识别到当前项目的阻塞项。" /> : issues.map((issue) => <IssueRow key={issue.key} issue={issue} />)
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function TabButtons<T extends string>({
  tabs,
  activeTab,
  onChange
}: {
  tabs: Array<{ id: T; label: string }>;
  activeTab: T;
  onChange: (tab: T) => void;
}) {
  return (
    <div className="flex h-10 shrink-0 items-center gap-2 border-b border-[var(--studio-color-border)] px-3 text-xs">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" aria-pressed={activeTab === tab.id} className={cn("rounded px-2 py-1.5 transition", activeTab === tab.id ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]" : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]")} onClick={() => onChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function CompactDrawer({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[var(--studio-z-dialog)] bg-black/45" data-testid="studio-formal-compact-drawer" onClick={onClose}>
      <div className="absolute right-0 top-0 h-full w-[min(440px,calc(100vw-48px))] border-l border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] shadow-2xl" role="dialog" aria-label={title} onClick={(event) => event.stopPropagation()}>
        <div className="flex h-11 items-center justify-between border-b border-[var(--studio-color-border)] px-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button type="button" aria-label="关闭抽屉" className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="h-[calc(100%-44px)] overflow-hidden">{children}</div>
      </div>
    </div>
  );
}

function MiniPanel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3"><h3 className="text-xs font-semibold text-[#cfd2ff]">{title}</h3><div className="mt-3">{children}</div></section>;
}

function StudioCard({ title, children }: { title: string; children: ReactNode }) {
  return <section className="mt-4 rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4"><h2 className="text-sm font-semibold">{title}</h2><div className="mt-3">{children}</div></section>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4"><div className="text-xs text-[var(--studio-color-text-muted)]">{label}</div><div className="mt-2 text-2xl font-semibold">{value}</div></div>;
}

function QuickEntry({ title, detail, href }: { title: string; detail: string; href: string }) {
  return <Link to={href} className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4 transition hover:border-[var(--studio-color-primary)]"><div className="flex items-center justify-between gap-3"><span className="font-semibold">{title}</span><ExternalLink className="h-4 w-4 text-[var(--studio-color-primary)]" /></div><p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">{detail}</p></Link>;
}

function InlineEmpty({ title, detail }: { title: string; detail: string }) {
  return <div className="rounded-[var(--studio-radius-card)] border border-dashed border-[var(--studio-color-border-strong)] p-4 text-sm"><div className="font-semibold">{title}</div><p className="mt-1 text-xs leading-5 text-[var(--studio-color-text-muted)]">{detail}</p></div>;
}

function AssetGroup({ title, empty, children }: { title: string; empty: string; children: ReactNode[] | ReactNode }) {
  const childArray = Array.isArray(children) ? children : [children];
  return <section><h3 className="mb-2 text-xs font-semibold text-[#cfd2ff]">{title}</h3><div className="space-y-2">{childArray.length > 0 ? children : <InlineEmpty title={empty} detail="从资产库创建后会出现在这里。" />}</div></section>;
}

function AssetButton({ active, label, detail, onClick }: { active: boolean; label: string; detail: string; onClick: () => void }) {
  return <button type="button" className={cn("w-full rounded-[var(--studio-radius-card)] border p-3 text-left transition hover:border-[var(--studio-color-primary)]", active ? "border-[var(--studio-color-primary)] bg-[var(--studio-color-primary-soft)]" : "border-[var(--studio-color-border)] bg-[var(--studio-color-surface)]")} onClick={onClick}><div className="truncate text-sm font-semibold">{label}</div><div className="mt-1 text-xs text-[var(--studio-color-text-muted)]">{detail}</div></button>;
}

function ProductionTile({ title, status }: { title: string; status: string | undefined }) {
  return <div className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4"><div className="text-xs text-[var(--studio-color-text-muted)]">{title}</div><div className="mt-2 text-sm font-semibold">{productionLabel(status)}</div></div>;
}

function TaskRow({ task }: { task: GenerationTaskSummary }) {
  return <Link to={`/projects/${task.project_id}/shots/${task.shot_id}`} className="mt-2 block rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3 hover:border-[var(--studio-color-primary)]"><div className="text-xs text-[var(--studio-color-text-muted)]">{task.task_type === "keyframe" ? "关键帧" : "视频"} / {task.latest_run_status ?? "无运行"}</div><div className="mt-1 text-sm font-semibold">{task.task_name}</div></Link>;
}

function IssueRow({ issue }: { issue: StudioIssue }) {
  return <div className="mt-2 rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3"><div className="flex items-center gap-2 text-sm font-semibold"><AlertTriangle className={cn("h-4 w-4", issue.tone === "danger" ? "text-[var(--studio-color-danger)]" : "text-[var(--studio-color-warning)]")} />{issue.title}</div><p className="mt-1 text-xs leading-5 text-[var(--studio-color-text-muted)]">{issue.detail}</p></div>;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between gap-4"><dt className="text-[var(--studio-color-text-muted)]">{label}</dt><dd className="text-right">{value}</dd></div>;
}

function stageLabel(status: StudioStage["status"]) {
  const labels: Record<StudioStage["status"], string> = {
    completed: "已完成",
    current: "当前",
    not_started: "未开始",
    blocked: "阻塞"
  };
  return labels[status];
}

function productionLabel(status: string | undefined) {
  const labels: Record<string, string> = {
    not_created: "未创建",
    draft: "草稿",
    ready: "就绪",
    running: "生成中",
    completed: "已完成",
    adopted: "已采用",
    missing_inputs: "缺少输入"
  };
  return status ? labels[status] ?? status : "暂无";
}
