import {
  Bell,
  Blocks,
  Check,
  ChevronDown,
  Clapperboard,
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
  Search,
  Settings,
  Sparkles,
  UserRound,
  Wand2,
  X
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent
} from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import {
  STUDIO_SHELL_DEFAULTS,
  STUDIO_SHELL_LIMITS,
  type ResizablePanel,
  type StudioShellLayoutState,
  clamp,
  createDefaultStudioShellLayout,
  isEditableTarget,
  loadStudioShellLayout,
  saveStudioShellLayout
} from "../layout-state";
import { StudioStatusBadge } from "./studio-status-badge";

const demoProjectId = "studio-ui-demo";

const navItems = [
  { label: "项目", icon: FolderKanban },
  { label: "Studio", icon: Sparkles },
  { label: "角色库", icon: UserRound },
  { label: "场景库", icon: Image },
  { label: "镜头", icon: Clapperboard },
  { label: "生成中心", icon: Wand2 },
  { label: "时间线", icon: LayoutDashboard },
  { label: "导出", icon: Blocks },
  { label: "设置", icon: Settings }
] as const;

const workspaceTabs = ["故事板", "工作流画布", "镜头生成控制台"] as const;
const inspectorTabs = ["信息", "生成", "历史"] as const;
const bottomTabs = ["时间线", "运行任务", "生成队列", "问题"] as const;

const statusSamples = [
  ["草稿", "draft"],
  ["就绪", "ready"],
  ["排队中", "running"],
  ["生成中", "running"],
  ["已完成", "success"],
  ["失败", "danger"],
  ["已中断", "warning"],
  ["可用", "success"],
  ["不可用", "danger"],
  ["已采用", "success"],
  ["未采用", "draft"]
] as const;

interface DragSession {
  panel: ResizablePanel;
  startX: number;
  startY: number;
  startValue: number;
}

function getPanelWidth(layout: StudioShellLayoutState, panel: "left" | "right") {
  if (layout.focusMode) {
    return 0;
  }

  if (panel === "left") {
    return layout.leftPanelCollapsed ? 0 : layout.leftWidth;
  }

  return layout.rightPanelCollapsed ? 0 : layout.rightWidth;
}

function isPanelVisible(width: number) {
  return width > 0;
}

export function StudioShellDemo() {
  const [layout, setLayout] = useState<StudioShellLayoutState>(() =>
    loadStudioShellLayout(demoProjectId)
  );
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window === "undefined" ? 1440 : window.innerWidth
  );
  const [activeNav, setActiveNav] = useState("Studio");
  const [activeWorkspaceTab, setActiveWorkspaceTab] =
    useState<(typeof workspaceTabs)[number]>("故事板");
  const [activeInspectorTab, setActiveInspectorTab] =
    useState<(typeof inspectorTabs)[number]>("信息");
  const [activeBottomTab, setActiveBottomTab] = useState<(typeof bottomTabs)[number]>("时间线");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [smartStartOpen, setSmartStartOpen] = useState(false);
  const [switchOn, setSwitchOn] = useState(true);
  const [selectValue, setSelectValue] = useState("电影感");
  const [textValue, setTextValue] = useState("");
  const [notesValue, setNotesValue] = useState("");
  const [secondaryStatus, setSecondaryStatus] = useState("尚未触发次按钮");
  const [localTab, setLocalTab] = useState<"样式" | "状态">("样式");
  const [compactDrawer, setCompactDrawer] = useState<"left" | "right" | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const dragSessionRef = useRef<DragSession | null>(null);

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    saveStudioShellLayout(demoProjectId, layout);
  }, [layout]);

  const updateLayout = useCallback((updater: (current: StudioShellLayoutState) => StudioShellLayoutState) => {
    setLayout((current) => updater(current));
  }, []);

  const showToast = useCallback((message: string) => {
    setToastMessage(message);
  }, []);

  const resetLayout = useCallback(() => {
    setCompactDrawer(null);
    setLayout(createDefaultStudioShellLayout());
    showToast("布局已恢复默认");
  }, [showToast]);

  const startResize = useCallback(
    (panel: ResizablePanel) => (event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      const startValue =
        panel === "left"
          ? layout.leftWidth
          : panel === "right"
            ? layout.rightWidth
            : layout.bottomHeight;

      dragSessionRef.current = {
        panel,
        startX: event.clientX,
        startY: event.clientY,
        startValue
      };
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
      showToast("面板尺寸已恢复默认");
    },
    [showToast, updateLayout]
  );

  const clampPanelResize = useCallback(
    (current: StudioShellLayoutState, panel: "left" | "right", requestedWidth: number) => {
      const navWidthForLayout =
        current.navCollapsed || viewportWidth < 768
          ? STUDIO_SHELL_LIMITS.navCollapsed
          : STUDIO_SHELL_LIMITS.navExpanded;
      const centerMinimumWidth = viewportWidth >= 1440 ? 560 : 360;
      const splitterWidth = 8;

      if (panel === "left") {
        const otherWidth = current.rightPanelCollapsed || current.focusMode ? 0 : current.rightWidth;
        const dynamicMax =
          viewportWidth - navWidthForLayout - otherWidth - centerMinimumWidth - splitterWidth;
        return clamp(
          requestedWidth,
          STUDIO_SHELL_LIMITS.leftMin,
          Math.min(STUDIO_SHELL_LIMITS.leftMax, Math.max(STUDIO_SHELL_LIMITS.leftMin, dynamicMax))
        );
      }

      const otherWidth = current.leftPanelCollapsed || current.focusMode ? 0 : current.leftWidth;
      const dynamicMax =
        viewportWidth - navWidthForLayout - otherWidth - centerMinimumWidth - splitterWidth;
      return clamp(
        requestedWidth,
        STUDIO_SHELL_LIMITS.rightMin,
        Math.min(STUDIO_SHELL_LIMITS.rightMax, Math.max(STUDIO_SHELL_LIMITS.rightMin, dynamicMax))
      );
    },
    [viewportWidth]
  );

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      const session = dragSessionRef.current;
      if (!session) {
        return;
      }

      updateLayout((current) => {
        if (session.panel === "left") {
          return {
            ...current,
            leftPanelCollapsed: false,
            leftWidth: clampPanelResize(
              current,
              "left",
              session.startValue + event.clientX - session.startX
            )
          };
        }

        if (session.panel === "right") {
          return {
            ...current,
            rightPanelCollapsed: false,
            rightWidth: clampPanelResize(
              current,
              "right",
              session.startValue - (event.clientX - session.startX)
            )
          };
        }

        return {
          ...current,
          bottomExpanded: true,
          bottomHeight: clamp(
            session.startValue - (event.clientY - session.startY),
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
      dragSessionRef.current = null;
      setIsResizing(false);
    };
  }, [clampPanelResize, updateLayout]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab" || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
      }
      if (isEditableTarget(event.target)) {
        return;
      }

      event.preventDefault();
      updateLayout((current) => ({ ...current, focusMode: !current.focusMode }));
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [updateLayout]);

  const compactMode = viewportWidth < 1200;
  const navWidth =
    layout.navCollapsed || viewportWidth < 768
      ? STUDIO_SHELL_LIMITS.navCollapsed
      : STUDIO_SHELL_LIMITS.navExpanded;
  const leftWidth = compactMode ? 0 : getPanelWidth(layout, "left");
  const rightWidth = compactMode ? 0 : getPanelWidth(layout, "right");
  const bottomHeight =
    layout.focusMode || !layout.bottomExpanded
      ? STUDIO_SHELL_LIMITS.bottomCollapsed
      : layout.bottomHeight;
  const showLeftPanel = isPanelVisible(leftWidth);
  const showRightPanel = isPanelVisible(rightWidth);
  const showLeftCompactDrawer = compactMode && compactDrawer === "left";

  const layoutSummary = useMemo(
    () => `左 ${layout.leftWidth}px / 右 ${layout.rightWidth}px / 底部 ${layout.bottomHeight}px`,
    [layout.bottomHeight, layout.leftWidth, layout.rightWidth]
  );

  return (
    <div
      className="studio-shell-demo h-screen min-h-[640px] overflow-hidden bg-[var(--studio-color-page)] text-[var(--studio-color-text)]"
      data-testid="studio-shell-demo"
    >
      <div className="flex h-full min-w-0 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--studio-color-border)] bg-[var(--studio-color-workspace)] px-3">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              aria-expanded={!layout.navCollapsed}
              aria-label={layout.navCollapsed ? "展开全局导航" : "折叠全局导航"}
              className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--studio-radius-button)] text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)]"
              onClick={() => updateLayout((current) => ({ ...current, navCollapsed: !current.navCollapsed }))}
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">Local Drama Studio 2.0</div>
              <div className="truncate text-xs text-[var(--studio-color-text-muted)]">
                当前模块：{activeNav} · {activeWorkspaceTab}
              </div>
            </div>
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <StudioStatusBadge tone="success">ComfyUI 已连接</StudioStatusBadge>
            <StudioStatusBadge tone="success">FFmpeg 正常</StudioStatusBadge>
            <button
              type="button"
              className="hidden h-9 items-center gap-2 rounded-[var(--studio-radius-button)] border border-[var(--studio-color-border)] px-3 text-xs text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)] md:inline-flex"
              onClick={() => showToast("搜索入口已触发")}
            >
              <Search className="h-4 w-4" />
              搜索
            </button>
            <button
              type="button"
              aria-label="通知"
              className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--studio-radius-button)] text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)]"
              onClick={() => showToast("当前没有新的系统通知")}
            >
              <Bell className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="inline-flex h-9 items-center gap-2 rounded-[var(--studio-radius-button)] border border-[var(--studio-color-border)] px-3 text-xs text-[var(--studio-color-text-secondary)] transition hover:bg-[var(--studio-color-hover)]"
              onClick={() => showToast("导演菜单示例已打开")}
            >
              导演
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <aside
            className="flex shrink-0 flex-col border-r border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] transition-[width] duration-[var(--studio-motion-panel)]"
            style={{ width: navWidth }}
            data-testid="studio-global-nav"
          >
            <nav className="space-y-1 p-2" aria-label="Studio 2.0 全局导航">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeNav === item.label;
                return (
                  <button
                    key={item.label}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => {
                      setActiveNav(item.label);
                      showToast(`已切换到 ${item.label} 示例模块`);
                    }}
                    className={cn(
                      "flex h-10 w-full items-center gap-3 rounded-[var(--studio-radius-button)] px-3 text-sm transition duration-[var(--studio-motion-fast)]",
                      isActive
                        ? "bg-[var(--studio-color-primary-soft)] text-[var(--studio-color-text)]"
                        : "text-[var(--studio-color-text-secondary)] hover:bg-[var(--studio-color-hover)]"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className={cn("truncate", layout.navCollapsed && "sr-only")}>
                      {item.label}
                    </span>
                  </button>
                );
              })}
            </nav>
          </aside>

          {showLeftPanel ? (
            <LeftContextPanel
              activeWorkspaceTab={activeWorkspaceTab}
              width={leftWidth}
              onCollapse={() =>
                updateLayout((current) => ({ ...current, leftPanelCollapsed: true }))
              }
              onToast={showToast}
            />
          ) : null}

          <div
            aria-label="调整左侧上下文面板宽度"
            role="separator"
            tabIndex={0}
            data-testid="left-resizer"
            className={cn(
              "z-[var(--studio-z-panel)] w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-[var(--studio-color-primary)]/50",
              (layout.focusMode || compactMode) && "hidden"
            )}
            onPointerDown={startResize("left")}
            onDoubleClick={() => resetPanel("left")}
          />

          <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[var(--studio-color-workspace)]">
            <div className="flex h-10 shrink-0 items-center justify-between border-b border-[var(--studio-color-border)] px-4">
              <div className="flex min-w-0 items-center gap-2">
                {workspaceTabs.map((tabName) => (
                  <button
                    key={tabName}
                    type="button"
                    aria-pressed={activeWorkspaceTab === tabName}
                    className={cn(
                      "rounded-[var(--studio-radius-button)] px-3 py-1.5 text-sm transition",
                      activeWorkspaceTab === tabName
                        ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]"
                        : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
                    )}
                    onClick={() => {
                      setActiveWorkspaceTab(tabName);
                      showToast(`中央视图已切换：${tabName}`);
                    }}
                  >
                    {tabName}
                  </button>
                ))}
              </div>

              <div className="flex shrink-0 items-center gap-2">
                {compactMode ? (
                  <>
                    <Button type="button" variant="secondary" size="sm" onClick={() => setCompactDrawer("left")}>
                      上下文
                    </Button>
                    <Button type="button" variant="secondary" size="sm" onClick={() => setCompactDrawer("right")}>
                      Inspector
                    </Button>
                  </>
                ) : null}
                {!showLeftPanel && !layout.focusMode && !compactMode ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => updateLayout((current) => ({ ...current, leftPanelCollapsed: false }))}
                  >
                    展开左栏
                  </Button>
                ) : null}
                {!showRightPanel && !layout.focusMode && !compactMode ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => updateLayout((current) => ({ ...current, rightPanelCollapsed: false }))}
                  >
                    展开 Inspector
                  </Button>
                ) : null}
                <Button type="button" variant="secondary" size="sm" onClick={resetLayout}>
                  <RefreshCcw className="h-4 w-4" />
                  恢复默认布局
                </Button>
                <Button
                  type="button"
                  variant={layout.focusMode ? "default" : "secondary"}
                  size="sm"
                  onClick={() => updateLayout((current) => ({ ...current, focusMode: !current.focusMode }))}
                >
                  {layout.focusMode ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  {layout.focusMode ? "退出专注" : "专注模式"}
                </Button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-hidden">
              <CenterWorkspace
                activeTab={activeWorkspaceTab}
                onSmartStart={() => setSmartStartOpen(true)}
                onToast={showToast}
              />
            </div>

            <div
              aria-label="调整底部工作区高度"
              role="separator"
              tabIndex={0}
              data-testid="bottom-resizer"
              className={cn(
                "h-1 shrink-0 cursor-row-resize bg-transparent hover:bg-[var(--studio-color-primary)]/50",
                layout.focusMode && "hidden"
              )}
              onPointerDown={startResize("bottom")}
              onDoubleClick={() => resetPanel("bottom")}
            />

            <section
              className="shrink-0 border-t border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] transition-[height] duration-[var(--studio-motion-panel)]"
              style={{ height: bottomHeight }}
              data-testid="studio-bottom-panel"
            >
              <div className="flex h-9 items-center justify-between px-4">
                <div className="flex min-w-0 items-center gap-3 text-xs">
                  <button
                    type="button"
                    className="text-[#cfd2ff]"
                    onClick={() =>
                      updateLayout((current) => ({
                        ...current,
                        bottomExpanded: !current.bottomExpanded
                      }))
                    }
                  >
                    {layout.bottomExpanded ? "底部工作区" : "任务状态：空闲"}
                  </button>
                  {layout.bottomExpanded
                    ? bottomTabs.map((tabName) => (
                        <button
                          key={tabName}
                          type="button"
                          aria-pressed={activeBottomTab === tabName}
                          className={cn(
                            "rounded px-2 py-1 transition",
                            activeBottomTab === tabName
                              ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]"
                              : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
                          )}
                          onClick={() => setActiveBottomTab(tabName)}
                        >
                          {tabName}
                        </button>
                      ))
                    : null}
                </div>
                <button
                  type="button"
                  aria-label={layout.bottomExpanded ? "折叠底部工作区" : "展开底部工作区"}
                  className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
                  onClick={() =>
                    updateLayout((current) => ({ ...current, bottomExpanded: !current.bottomExpanded }))
                  }
                >
                  <PanelBottomOpen className="h-4 w-4" />
                </button>
              </div>
              {layout.bottomExpanded ? (
                <BottomWorkspace
                  activeTab={activeBottomTab}
                  dialogOpen={dialogOpen}
                  confirmOpen={confirmOpen}
                  onDialogOpenChange={setDialogOpen}
                  onConfirmOpenChange={setConfirmOpen}
                  onToast={showToast}
                  selectValue={selectValue}
                  onSelectValueChange={setSelectValue}
                  switchOn={switchOn}
                  onSwitchChange={setSwitchOn}
                  textValue={textValue}
                  onTextChange={setTextValue}
                  notesValue={notesValue}
                  onNotesChange={setNotesValue}
                  secondaryStatus={secondaryStatus}
                  onSecondaryStatusChange={setSecondaryStatus}
                  localTab={localTab}
                  onLocalTabChange={setLocalTab}
                />
              ) : null}
            </section>
          </main>

          <div
            aria-label="调整 Inspector 宽度"
            role="separator"
            tabIndex={0}
            data-testid="right-resizer"
            className={cn(
              "z-[var(--studio-z-panel)] w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-[var(--studio-color-primary)]/50",
              (layout.focusMode || compactMode) && "hidden"
            )}
            onPointerDown={startResize("right")}
            onDoubleClick={() => resetPanel("right")}
          />

          {showRightPanel ? (
            <RightInspector
              activeTab={activeInspectorTab}
              layoutSummary={layoutSummary}
              width={rightWidth}
              onActiveTabChange={setActiveInspectorTab}
              onCollapse={() =>
                updateLayout((current) => ({ ...current, rightPanelCollapsed: true }))
              }
              selectValue={selectValue}
              onSelectValueChange={setSelectValue}
              switchOn={switchOn}
              onSwitchChange={setSwitchOn}
              onToast={showToast}
            />
          ) : null}
        </div>
      </div>

      {compactMode && compactDrawer ? (
        <CompactDrawer
          side={compactDrawer}
          onClose={() => setCompactDrawer(null)}
          showLeft={showLeftCompactDrawer}
        />
      ) : null}
      {smartStartOpen ? (
        <SimpleDialog
          title="智能续作起点页预览"
          description="Sprint 27A 仅展示可交互外壳。Sprint 27B 会接入真实智能续作入口。"
          onClose={() => setSmartStartOpen(false)}
          onConfirm={() => {
            setSmartStartOpen(false);
            showToast("智能续作起点页预览已确认");
          }}
        />
      ) : null}
      {isResizing ? (
        <div
          className="fixed inset-0 z-[var(--studio-z-toast)] cursor-col-resize"
          data-testid="studio-resize-shield"
          aria-hidden="true"
        />
      ) : null}
      {toastMessage ? (
        <div
          className="pointer-events-none fixed right-4 top-16 z-[var(--studio-z-toast)] rounded-[var(--studio-radius-floating)] border border-[var(--studio-color-success)]/50 bg-[var(--studio-color-success-soft)] px-4 py-3 text-sm text-[#a7f3d0] shadow-2xl"
          role="status"
        >
          <div className="flex items-center gap-2">
            <Check className="h-4 w-4" />
            <span>{toastMessage}</span>
            <button
              type="button"
              aria-label="关闭提示"
              className="pointer-events-auto ml-2 rounded p-1 hover:bg-white/10"
              onClick={() => setToastMessage(null)}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function LeftContextPanel({
  activeWorkspaceTab,
  width,
  onCollapse,
  onToast
}: {
  activeWorkspaceTab: string;
  width: number;
  onCollapse: () => void;
  onToast: (message: string) => void;
}) {
  return (
    <section
      className="min-w-0 shrink-0 border-r border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]"
      style={{ width }}
      data-testid="studio-left-panel"
    >
      <div className="flex h-11 items-center justify-between border-b border-[var(--studio-color-border)] px-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-[#cfd2ff]">上下文面板</div>
          <div className="text-[11px] text-[var(--studio-color-text-muted)]">{activeWorkspaceTab} · 可折叠</div>
        </div>
        <button
          type="button"
          aria-label="折叠左侧上下文面板"
          className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
          onClick={onCollapse}
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-3 overflow-y-auto p-3">
        <label className="block text-xs text-[var(--studio-color-text-muted)]" htmlFor="studio-shot-search">
          镜头列表（7）
        </label>
        <input
          id="studio-shot-search"
          className="h-9 w-full rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] px-3 text-sm outline-none transition focus:border-[var(--studio-color-primary)]"
          placeholder="搜索镜头"
        />
        {["开场 establishing shot", "主人公推门", "手机讯息", "会议室中景", "全员回头"].map(
          (shot, index) => (
            <button
              key={shot}
              type="button"
              className={cn(
                "flex h-8 w-full items-center gap-2 rounded-[var(--studio-radius-button)] px-2 text-left text-xs transition",
                index === 0
                  ? "bg-[var(--studio-color-selected)] text-white"
                  : "text-[var(--studio-color-text-secondary)] hover:bg-[var(--studio-color-hover)]"
              )}
              onClick={() => onToast(`已选择镜头：${shot}`)}
            >
              <span className="w-6 text-[var(--studio-color-text-muted)]">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="truncate">{shot}</span>
            </button>
          )
        )}
      </div>
    </section>
  );
}

function CenterWorkspace({
  activeTab,
  onSmartStart,
  onToast
}: {
  activeTab: (typeof workspaceTabs)[number];
  onSmartStart: () => void;
  onToast: (message: string) => void;
}) {
  if (activeTab === "工作流画布") {
    return (
      <div className="h-full overflow-auto bg-[radial-gradient(circle_at_1px_1px,rgba(124,130,255,0.12)_1px,transparent_0)] p-8 [background-size:24px_24px]">
        <h1 className="text-xl font-semibold">工作流画布演示区域</h1>
        <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">
          这里展示未来节点画布的基础视觉，不暴露 ComfyUI 底层节点。
        </p>
        <div className="mt-8 grid max-w-3xl grid-cols-3 gap-4">
          {["角色节点", "镜头节点", "视频输出"].map((label, index) => (
            <button
              key={label}
              type="button"
              className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-5 text-left transition hover:border-[var(--studio-color-primary)]"
              onClick={() => onToast(`已选中${label}`)}
            >
              <div className="text-sm font-semibold">{label}</div>
              <div className="mt-8 text-xs text-[var(--studio-color-text-muted)]">
                节点 {index + 1} · 可拖拽占位
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === "镜头生成控制台") {
    return (
      <div className="h-full overflow-auto p-8">
        <h1 className="text-xl font-semibold">镜头生成控制台演示区域</h1>
        <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">
          这里只演示快速创作入口的外壳，不触发真实生成。
        </p>
        <div className="mt-6 max-w-3xl rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-5">
          <label className="text-xs text-[var(--studio-color-text-muted)]" htmlFor="center-prompt">
            Prompt 示例
          </label>
          <textarea
            id="center-prompt"
            className="mt-2 min-h-24 w-full resize-none rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3 text-sm outline-none focus:border-[var(--studio-color-primary)]"
            placeholder="男主推门进入会议室，所有人震惊回头。"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <StudioStatusBadge tone="ready">角色参考已选</StudioStatusBadge>
            <StudioStatusBadge tone="warning">尾帧待生成</StudioStatusBadge>
            <StudioStatusBadge tone="draft">视频未开始</StudioStatusBadge>
          </div>
          <Button
            type="button"
            className="mt-5 bg-[var(--studio-color-primary)] hover:bg-[var(--studio-color-primary-hover)]"
            onClick={() => onToast("生成按钮示例已触发")}
          >
            生成首帧示例
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-8">
      <h1 className="text-xl font-semibold">故事板演示区域</h1>
      <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">
        这里使用本地占位卡片验证视图切换，不读取真实业务数据。
      </p>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {["01 开场", "02 推门", "03 全员回头"].map((title) => (
          <button
            key={title}
            type="button"
            className="rounded-[var(--studio-radius-preview)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-4 text-left transition hover:border-[var(--studio-color-primary)]"
            onClick={() => onToast(`已打开故事板卡片：${title}`)}
          >
            <div className="aspect-video rounded-[var(--studio-radius-card)] border border-dashed border-[var(--studio-color-border-strong)] bg-[var(--studio-color-page)]" />
            <div className="mt-3 text-sm font-semibold">{title}</div>
            <div className="mt-1 text-xs text-[var(--studio-color-text-muted)]">人物 2 · 场景 1 · 草稿</div>
          </button>
        ))}
      </div>
      <Button
        type="button"
        className="mt-6 bg-[var(--studio-color-primary)] hover:bg-[var(--studio-color-primary-hover)]"
        onClick={onSmartStart}
      >
        打开智能续作起点页
      </Button>
    </div>
  );
}

function RightInspector({
  activeTab,
  layoutSummary,
  width,
  onActiveTabChange,
  onCollapse,
  selectValue,
  onSelectValueChange,
  switchOn,
  onSwitchChange,
  onToast
}: {
  activeTab: (typeof inspectorTabs)[number];
  layoutSummary: string;
  width: number;
  onActiveTabChange: (tab: (typeof inspectorTabs)[number]) => void;
  onCollapse: () => void;
  selectValue: string;
  onSelectValueChange: (value: string) => void;
  switchOn: boolean;
  onSwitchChange: (value: boolean) => void;
  onToast: (message: string) => void;
}) {
  return (
    <aside
      className="min-w-0 shrink-0 border-l border-[var(--studio-color-border)] bg-[var(--studio-color-panel)]"
      style={{ width }}
      data-testid="studio-right-panel"
    >
      <div className="flex h-11 items-center justify-between border-b border-[var(--studio-color-border)] px-3">
        <div>
          <div className="text-xs font-semibold text-[#cfd2ff]">Inspector</div>
          <div className="text-[11px] text-[var(--studio-color-text-muted)]">可调整 · 可折叠</div>
        </div>
        <button
          type="button"
          aria-label="折叠 Inspector"
          className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
          onClick={onCollapse}
        >
          <PanelRightClose className="h-4 w-4" />
        </button>
      </div>
      <div className="flex h-[calc(100%-44px)] min-h-0 flex-col">
        <div className="flex h-10 shrink-0 items-center gap-4 border-b border-[var(--studio-color-border)] px-4 text-xs">
          {inspectorTabs.map((tabName) => (
            <button
              key={tabName}
              type="button"
              aria-pressed={activeTab === tabName}
              className={cn(
                "py-3 transition",
                activeTab === tabName
                  ? "border-b border-[var(--studio-color-primary)] text-[#dfe1ff]"
                  : "text-[var(--studio-color-text-muted)] hover:text-[var(--studio-color-text)]"
              )}
              onClick={() => onActiveTabChange(tabName)}
            >
              {tabName}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {activeTab === "信息" ? (
            <div>
              <h2 className="text-base font-semibold">当前示例镜头摘要</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--studio-color-text-muted)]">镜头</dt>
                  <dd>01 开场 establishing shot</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--studio-color-text-muted)]">布局</dt>
                  <dd>{layoutSummary}</dd>
                </div>
              </dl>
            </div>
          ) : null}
          {activeTab === "生成" ? (
            <div className="space-y-4">
              <h2 className="text-base font-semibold">生成参数面板</h2>
              <label className="block text-xs text-[var(--studio-color-text-muted)]" htmlFor="inspector-prompt">
                Prompt
              </label>
              <textarea
                id="inspector-prompt"
                className="min-h-24 w-full resize-none rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3 text-sm outline-none focus:border-[var(--studio-color-primary)]"
                placeholder="这里是 Inspector Prompt 示例"
              />
              <select
                aria-label="Inspector 风格选择"
                className="h-9 w-full rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] px-3 text-sm"
                value={selectValue}
                onChange={(event) => onSelectValueChange(event.target.value)}
              >
                <option>电影感</option>
                <option>纪实感</option>
                <option>商业质感</option>
              </select>
              <button
                type="button"
                role="switch"
                aria-label="自动保存开关"
                aria-checked={switchOn}
                className="flex h-9 w-full items-center justify-between rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] px-3 text-sm"
                onClick={() => onSwitchChange(!switchOn)}
              >
                <span>自动保存 {switchOn ? "开" : "关"}</span>
                <span className="text-[var(--studio-color-text-muted)]">{switchOn ? "ON" : "OFF"}</span>
              </button>
              <Button type="button" onClick={() => onToast("Inspector 生成按钮示例已触发")}>
                生成示例
              </Button>
            </div>
          ) : null}
          {activeTab === "历史" ? (
            <div>
              <h2 className="text-base font-semibold">历史操作记录</h2>
              <div className="mt-4 space-y-3">
                {["Run #1 · completed", "Run #2 · failed", "Run #3 · draft"].map((item) => (
                  <div
                    key={item}
                    className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-3 text-sm"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

interface BottomWorkspaceProps {
  activeTab: (typeof bottomTabs)[number];
  dialogOpen: boolean;
  confirmOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
  onConfirmOpenChange: (open: boolean) => void;
  onToast: (message: string) => void;
  selectValue: string;
  onSelectValueChange: (value: string) => void;
  switchOn: boolean;
  onSwitchChange: (value: boolean) => void;
  textValue: string;
  onTextChange: (value: string) => void;
  notesValue: string;
  onNotesChange: (value: string) => void;
  secondaryStatus: string;
  onSecondaryStatusChange: (value: string) => void;
  localTab: "样式" | "状态";
  onLocalTabChange: (value: "样式" | "状态") => void;
}

function BottomWorkspace(props: BottomWorkspaceProps) {
  return (
    <div className="grid h-[calc(100%-36px)] min-h-0 grid-cols-1 gap-4 overflow-y-auto px-4 pb-4 xl:grid-cols-[1fr_1.3fr]">
      <section className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-4">
        <h2 className="text-sm font-semibold">{props.activeTab}演示内容</h2>
        <div className="mt-4 text-sm text-[var(--studio-color-text-muted)]">
          {props.activeTab === "时间线" ? "时间线：镜头 01 → 镜头 02 → 镜头 03" : null}
          {props.activeTab === "运行任务" ? "运行任务：当前没有进行中的任务。" : null}
          {props.activeTab === "生成队列" ? "生成队列：首帧候选等待用户采用。" : null}
          {props.activeTab === "问题" ? "问题：当前没有阻断项。" : null}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {statusSamples.map(([label, tone]) => (
            <StudioStatusBadge key={label} tone={tone}>
              {label}
            </StudioStatusBadge>
          ))}
        </div>
      </section>
      <ComponentDemo {...props} />
    </div>
  );
}

function ComponentDemo({
  dialogOpen,
  confirmOpen,
  onDialogOpenChange,
  onConfirmOpenChange,
  onToast,
  selectValue,
  onSelectValueChange,
  switchOn,
  onSwitchChange,
  textValue,
  onTextChange,
  notesValue,
  onNotesChange,
  secondaryStatus,
  onSecondaryStatusChange,
  localTab,
  onLocalTabChange
}: BottomWorkspaceProps) {
  const [loading, setLoading] = useState(false);

  return (
    <section className="rounded-[var(--studio-radius-card)] border border-[var(--studio-color-border)] bg-[var(--studio-color-surface)] p-4">
      <h2 className="text-sm font-semibold">组件演示</h2>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => onToast("Primary Button 已触发")}>Primary Button</Button>
        <Button
          variant="secondary"
          onClick={() => onSecondaryStatusChange("Secondary Button 已更新本地状态")}
        >
          Secondary Button
        </Button>
        <Button variant="secondary" onClick={() => onDialogOpenChange(true)}>
          Dialog Button
        </Button>
        <Button variant="secondary" onClick={() => onConfirmOpenChange(true)}>
          Confirm Dialog
        </Button>
        <Button disabled>Disabled Button</Button>
        <Button
          disabled={loading}
          onClick={() => {
            setLoading(true);
            window.setTimeout(() => setLoading(false), 600);
          }}
        >
          {loading ? (
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          ) : null}
          {loading ? "Loading..." : "Loading Button"}
        </Button>
      </div>
      <p className="mt-3 text-sm text-[var(--studio-color-text-muted)]">{secondaryStatus}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="text-xs text-[var(--studio-color-text-muted)]">
          Select
          <select
            aria-label="Demo 下拉选择"
            className="mt-1 h-9 w-full rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-page)] px-3 text-sm"
            value={selectValue}
            onChange={(event) => onSelectValueChange(event.target.value)}
          >
            <option>电影感</option>
            <option>纪实感</option>
            <option>商业质感</option>
          </select>
        </label>
        <button
          type="button"
          role="switch"
          aria-label="Demo Switch"
          aria-checked={switchOn}
          className="mt-5 flex h-9 items-center justify-between rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-page)] px-3 text-sm"
          onClick={() => onSwitchChange(!switchOn)}
        >
          <span>Switch：{switchOn ? "开" : "关"}</span>
          <span className="text-[var(--studio-color-text-muted)]">{switchOn ? "ON" : "OFF"}</span>
        </button>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="text-xs text-[var(--studio-color-text-muted)]">
          TextInput
          <input
            className="mt-1 h-9 w-full rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-page)] px-3 text-sm"
            value={textValue}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="输入镜头标题"
          />
        </label>
        <label className="text-xs text-[var(--studio-color-text-muted)]">
          TextArea
          <textarea
            className="mt-1 min-h-20 w-full resize-none rounded-[var(--studio-radius-input)] border border-[var(--studio-color-border)] bg-[var(--studio-color-page)] p-3 text-sm"
            value={notesValue}
            onChange={(event) => onNotesChange(event.target.value)}
            placeholder="输入备注"
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-[var(--studio-color-text-muted)]">
        当前选择：{selectValue} · 输入长度：{textValue.length} · 备注字数：{notesValue.length}
      </p>
      <div className="mt-4 flex gap-2">
        {(["样式", "状态"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            aria-pressed={localTab === tab}
            className={cn(
              "rounded px-3 py-1.5 text-sm",
              localTab === tab
                ? "bg-[var(--studio-color-primary-soft)] text-[#dfe1ff]"
                : "text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
            )}
            onClick={() => onLocalTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="mt-3 rounded-[var(--studio-radius-card)] border border-dashed border-[var(--studio-color-border-strong)] p-3 text-sm text-[var(--studio-color-text-muted)]">
        Tabs 当前内容：{localTab === "样式" ? "按钮、输入框与 Badge 视觉规范。" : "草稿、就绪、失败、已采用等状态规范。"}
      </div>
      {dialogOpen ? (
        <SimpleDialog
          title="提示"
          description="这是一个 Dialog 示例，取消和确认都会关闭。"
          onClose={() => onDialogOpenChange(false)}
          onConfirm={() => {
            onDialogOpenChange(false);
            onToast("Dialog 已确认");
          }}
        />
      ) : null}
      {confirmOpen ? (
        <SimpleDialog
          title="确认操作"
          description="这是一个 Confirm Dialog 示例，不会触发真实业务。"
          onClose={() => onConfirmOpenChange(false)}
          onConfirm={() => {
            onConfirmOpenChange(false);
            onToast("Confirm Dialog 已确认");
          }}
        />
      ) : null}
    </section>
  );
}

function SimpleDialog({
  title,
  description,
  onClose,
  onConfirm
}: {
  title: string;
  description: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[var(--studio-z-dialog)] flex items-center justify-center bg-black/55"
      data-testid="studio-demo-dialog-overlay"
      role="presentation"
    >
      <div
        className="w-[min(420px,calc(100vw-32px))] rounded-[var(--studio-radius-floating)] border border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-5 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            <p className="mt-2 text-sm text-[var(--studio-color-text-muted)]">{description}</p>
          </div>
          <button
            type="button"
            aria-label="关闭弹窗"
            className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={onConfirm}>确认</Button>
        </div>
      </div>
    </div>
  );
}

function CompactDrawer({
  side,
  showLeft,
  onClose
}: {
  side: "left" | "right";
  showLeft: boolean;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[var(--studio-z-dialog)] bg-black/45"
      data-testid="compact-drawer-backdrop"
      onClick={onClose}
    >
      <div
        className={cn(
          "absolute top-0 h-full w-[min(420px,calc(100vw-48px))] border-[var(--studio-color-border)] bg-[var(--studio-color-panel)] p-4 shadow-2xl",
          showLeft ? "left-0 border-r" : "right-0 border-l"
        )}
        role="dialog"
        aria-label={side === "left" ? "上下文抽屉" : "Inspector 抽屉"}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">{side === "left" ? "上下文抽屉" : "Inspector 抽屉"}</h2>
          <button
            type="button"
            aria-label="关闭辅助抽屉"
            className="rounded-[var(--studio-radius-button)] p-2 text-[var(--studio-color-text-muted)] hover:bg-[var(--studio-color-hover)]"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-4 text-sm text-[var(--studio-color-text-muted)]">
          小屏下左右工作面板以抽屉方式出现，关闭后不会留下遮罩。
        </p>
      </div>
    </div>
  );
}
