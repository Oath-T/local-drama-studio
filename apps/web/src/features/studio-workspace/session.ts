export const STUDIO_SESSION_VERSION = 1;

export type StudioMode = "start" | "storyboard" | "workflow";
export type StudioView = "start" | "storyboard" | "workflow" | "shot_console";
export type StudioContextEntityType = "character" | "scene" | "shot" | null;
export type StudioContextTab = "overview" | "shots" | "assets";
export type StudioInspectorTab = "info" | "next";
export type StudioBottomTab = "running" | "issues";

export interface StudioSessionState {
  schemaVersion: typeof STUDIO_SESSION_VERSION;
  projectId: string;
  currentMode: StudioMode;
  currentView: StudioView;
  selectedShotId: string | null;
  selectedEntityType: StudioContextEntityType;
  selectedEntityId: string | null;
  leftPanelTab: StudioContextTab;
  inspectorTab: StudioInspectorTab;
  bottomPanelTab: StudioBottomTab;
  bottomPanelExpanded: boolean;
  lastRoute: string | null;
  updatedAt: string;
}

export interface StudioUrlContext {
  selectedShotId: string | null;
  selectedEntityType: StudioContextEntityType;
  selectedEntityId: string | null;
  intent: string | null;
  ignored: boolean;
}

export function getStudioSessionStorageKey(projectId: string) {
  return `lds:studio-session:v${STUDIO_SESSION_VERSION}:${projectId}`;
}

export function createDefaultStudioSession(projectId: string): StudioSessionState {
  return {
    schemaVersion: STUDIO_SESSION_VERSION,
    projectId,
    currentMode: "start",
    currentView: "start",
    selectedShotId: null,
    selectedEntityType: null,
    selectedEntityId: null,
    leftPanelTab: "overview",
    inspectorTab: "next",
    bottomPanelTab: "issues",
    bottomPanelExpanded: false,
    lastRoute: null,
    updatedAt: new Date(0).toISOString()
  };
}

function isStudioMode(value: unknown): value is StudioMode {
  return value === "start" || value === "storyboard" || value === "workflow";
}

function isStudioView(value: unknown): value is StudioView {
  return value === "start" || value === "storyboard" || value === "workflow" || value === "shot_console";
}

function isContextTab(value: unknown): value is StudioContextTab {
  return value === "overview" || value === "shots" || value === "assets";
}

function isInspectorTab(value: unknown): value is StudioInspectorTab {
  return value === "info" || value === "next";
}

function isBottomTab(value: unknown): value is StudioBottomTab {
  return value === "running" || value === "issues";
}

function isEntityType(value: unknown): value is Exclude<StudioContextEntityType, null> {
  return value === "character" || value === "scene" || value === "shot";
}

function nullableString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function normalizeStudioSession(projectId: string, value: unknown): StudioSessionState {
  if (!value || typeof value !== "object") {
    return createDefaultStudioSession(projectId);
  }

  const candidate = value as Partial<StudioSessionState>;
  if (candidate.schemaVersion !== STUDIO_SESSION_VERSION || candidate.projectId !== projectId) {
    return createDefaultStudioSession(projectId);
  }

  return {
    schemaVersion: STUDIO_SESSION_VERSION,
    projectId,
    currentMode: isStudioMode(candidate.currentMode) ? candidate.currentMode : "start",
    currentView: isStudioView(candidate.currentView) ? candidate.currentView : "start",
    selectedShotId: nullableString(candidate.selectedShotId),
    selectedEntityType: isEntityType(candidate.selectedEntityType) ? candidate.selectedEntityType : null,
    selectedEntityId: nullableString(candidate.selectedEntityId),
    leftPanelTab: isContextTab(candidate.leftPanelTab) ? candidate.leftPanelTab : "overview",
    inspectorTab: isInspectorTab(candidate.inspectorTab) ? candidate.inspectorTab : "next",
    bottomPanelTab: isBottomTab(candidate.bottomPanelTab) ? candidate.bottomPanelTab : "issues",
    bottomPanelExpanded: Boolean(candidate.bottomPanelExpanded),
    lastRoute: nullableString(candidate.lastRoute),
    updatedAt: nullableString(candidate.updatedAt) ?? new Date(0).toISOString()
  };
}

export function loadStudioSession(
  projectId: string,
  storage: Storage = window.localStorage
): StudioSessionState {
  try {
    const raw = storage.getItem(getStudioSessionStorageKey(projectId));
    return raw ? normalizeStudioSession(projectId, JSON.parse(raw)) : createDefaultStudioSession(projectId);
  } catch {
    return createDefaultStudioSession(projectId);
  }
}

export function saveStudioSession(
  session: StudioSessionState,
  storage: Storage = window.localStorage
) {
  storage.setItem(
    getStudioSessionStorageKey(session.projectId),
    JSON.stringify({ ...session, updatedAt: new Date().toISOString() })
  );
}

export function clearStudioSession(projectId: string, storage: Storage = window.localStorage) {
  storage.removeItem(getStudioSessionStorageKey(projectId));
}

export function parseStudioUrlContext(search: string): StudioUrlContext {
  const params = new URLSearchParams(search);
  const shotId = params.get("shotId");
  const entityType = params.get("entityType");
  const entityId = params.get("entityId");
  const intent = params.get("intent");
  const validEntityType = isEntityType(entityType) ? entityType : null;

  return {
    selectedShotId: nullableString(shotId),
    selectedEntityType: validEntityType,
    selectedEntityId: validEntityType ? nullableString(entityId) : null,
    intent: nullableString(intent),
    ignored: Boolean((entityType && !validEntityType) || (entityType && !entityId))
  };
}

export function sanitizeStudioSessionSelection(
  session: StudioSessionState,
  valid: {
    shotIds: Set<string>;
    characterIds: Set<string>;
    sceneIds: Set<string>;
  }
): StudioSessionState {
  let next = { ...session };
  if (next.selectedShotId && !valid.shotIds.has(next.selectedShotId)) {
    next = { ...next, selectedShotId: null };
  }

  if (
    next.selectedEntityType === "character" &&
    next.selectedEntityId &&
    !valid.characterIds.has(next.selectedEntityId)
  ) {
    next = { ...next, selectedEntityType: null, selectedEntityId: null };
  }

  if (
    next.selectedEntityType === "scene" &&
    next.selectedEntityId &&
    !valid.sceneIds.has(next.selectedEntityId)
  ) {
    next = { ...next, selectedEntityType: null, selectedEntityId: null };
  }

  return next;
}
