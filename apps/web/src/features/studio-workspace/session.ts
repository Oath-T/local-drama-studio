export const STUDIO_SESSION_VERSION = 3;

export interface StudioSessionState {
  schemaVersion: typeof STUDIO_SESSION_VERSION;
  projectId: string;
  selectedShotId: string | null;
  scrollPosition: number;
  updatedAt: string;
}

export interface StudioUrlContext {
  selectedShotId: string | null;
  intent: string | null;
  ignored: boolean;
}

export function getStudioSessionStorageKey(projectId: string) {
  return `lds:studio-session:v${STUDIO_SESSION_VERSION}:${projectId}`;
}

function getLegacyStudioSessionStorageKeys(projectId: string) {
  return [`lds:studio-session:v2:${projectId}`, `lds:studio-session:v1:${projectId}`];
}

export function createDefaultStudioSession(projectId: string): StudioSessionState {
  return {
    schemaVersion: STUDIO_SESSION_VERSION,
    projectId,
    selectedShotId: null,
    scrollPosition: 0,
    updatedAt: new Date(0).toISOString()
  };
}

function nullableString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function normalizeStudioSession(projectId: string, value: unknown): StudioSessionState {
  if (!value || typeof value !== "object") {
    return createDefaultStudioSession(projectId);
  }

  const candidate = value as Partial<StudioSessionState>;
  if (candidate.projectId !== projectId) {
    return createDefaultStudioSession(projectId);
  }

  return {
    schemaVersion: STUDIO_SESSION_VERSION,
    projectId,
    selectedShotId: nullableString(candidate.selectedShotId),
    scrollPosition:
      typeof candidate.scrollPosition === "number" && Number.isFinite(candidate.scrollPosition)
        ? Math.max(0, candidate.scrollPosition)
        : 0,
    updatedAt: nullableString(candidate.updatedAt) ?? new Date(0).toISOString()
  };
}

export function loadStudioSession(
  projectId: string,
  storage: Storage = window.localStorage
): StudioSessionState {
  try {
    const current = storage.getItem(getStudioSessionStorageKey(projectId));
    if (current) {
      return normalizeStudioSession(projectId, JSON.parse(current));
    }

    for (const key of getLegacyStudioSessionStorageKeys(projectId)) {
      const legacy = storage.getItem(key);
      if (legacy) {
        return normalizeStudioSession(projectId, JSON.parse(legacy));
      }
    }
  } catch {
    return createDefaultStudioSession(projectId);
  }

  return createDefaultStudioSession(projectId);
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
  const intent = params.get("intent");
  const hasIgnoredEntityParams = params.has("entityType") || params.has("entityId");

  return {
    selectedShotId: nullableString(shotId),
    intent: nullableString(intent),
    ignored: hasIgnoredEntityParams
  };
}

export function sanitizeStudioSessionSelection(
  session: StudioSessionState,
  validShotIds: Set<string>
): StudioSessionState {
  if (session.selectedShotId && !validShotIds.has(session.selectedShotId)) {
    return { ...session, selectedShotId: null };
  }

  return session;
}
