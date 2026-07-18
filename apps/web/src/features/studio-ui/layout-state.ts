export const STUDIO_SHELL_LAYOUT_VERSION = 1;

export const STUDIO_SHELL_DEFAULTS = {
  navCollapsed: true,
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  bottomExpanded: false,
  focusMode: false,
  leftWidth: 280,
  rightWidth: 440,
  bottomHeight: 260
} as const;

export const STUDIO_SHELL_LIMITS = {
  navExpanded: 200,
  navCollapsed: 64,
  leftMin: 220,
  leftMax: 480,
  rightMin: 360,
  rightMax: 720,
  bottomMin: 160,
  bottomMax: 560,
  bottomCollapsed: 36,
  topBar: 56
} as const;

export interface StudioShellLayoutState {
  version: typeof STUDIO_SHELL_LAYOUT_VERSION;
  navCollapsed: boolean;
  leftPanelCollapsed: boolean;
  rightPanelCollapsed: boolean;
  bottomExpanded: boolean;
  focusMode: boolean;
  leftWidth: number;
  rightWidth: number;
  bottomHeight: number;
}

export type ResizablePanel = "left" | "right" | "bottom";

export function getStudioShellStorageKey(projectId: string) {
  return `lds:studio-shell-layout:v${STUDIO_SHELL_LAYOUT_VERSION}:${projectId}`;
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function createDefaultStudioShellLayout(): StudioShellLayoutState {
  return {
    version: STUDIO_SHELL_LAYOUT_VERSION,
    ...STUDIO_SHELL_DEFAULTS
  };
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function normalizeStudioShellLayout(value: unknown): StudioShellLayoutState {
  if (!value || typeof value !== "object") {
    return createDefaultStudioShellLayout();
  }

  const candidate = value as Partial<StudioShellLayoutState>;
  if (candidate.version !== STUDIO_SHELL_LAYOUT_VERSION) {
    return createDefaultStudioShellLayout();
  }

  return {
    version: STUDIO_SHELL_LAYOUT_VERSION,
    navCollapsed: Boolean(candidate.navCollapsed),
    leftPanelCollapsed: Boolean(candidate.leftPanelCollapsed),
    rightPanelCollapsed: Boolean(candidate.rightPanelCollapsed),
    bottomExpanded: Boolean(candidate.bottomExpanded),
    focusMode: Boolean(candidate.focusMode),
    leftWidth: clamp(
      isFiniteNumber(candidate.leftWidth) ? candidate.leftWidth : STUDIO_SHELL_DEFAULTS.leftWidth,
      STUDIO_SHELL_LIMITS.leftMin,
      STUDIO_SHELL_LIMITS.leftMax
    ),
    rightWidth: clamp(
      isFiniteNumber(candidate.rightWidth) ? candidate.rightWidth : STUDIO_SHELL_DEFAULTS.rightWidth,
      STUDIO_SHELL_LIMITS.rightMin,
      STUDIO_SHELL_LIMITS.rightMax
    ),
    bottomHeight: clamp(
      isFiniteNumber(candidate.bottomHeight)
        ? candidate.bottomHeight
        : STUDIO_SHELL_DEFAULTS.bottomHeight,
      STUDIO_SHELL_LIMITS.bottomMin,
      STUDIO_SHELL_LIMITS.bottomMax
    )
  };
}

export function loadStudioShellLayout(projectId: string, storage: Storage = window.localStorage) {
  try {
    const rawValue = storage.getItem(getStudioShellStorageKey(projectId));
    if (!rawValue) {
      return createDefaultStudioShellLayout();
    }
    return normalizeStudioShellLayout(JSON.parse(rawValue));
  } catch {
    return createDefaultStudioShellLayout();
  }
}

export function saveStudioShellLayout(
  projectId: string,
  layout: StudioShellLayoutState,
  storage: Storage = window.localStorage
) {
  storage.setItem(getStudioShellStorageKey(projectId), JSON.stringify(layout));
}

export function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tagName = target.tagName.toLowerCase();
  return (
    tagName === "input" ||
    tagName === "textarea" ||
    tagName === "select" ||
    target.isContentEditable
  );
}
