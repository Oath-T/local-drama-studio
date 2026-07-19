import { describe, expect, it } from "vitest";

import {
  clearStudioSession,
  createDefaultStudioSession,
  getStudioSessionStorageKey,
  loadStudioSession,
  normalizeStudioSession,
  parseStudioUrlContext,
  sanitizeStudioSessionSelection,
  saveStudioSession
} from "./session";

describe("studio session persistence", () => {
  it("restores a valid project session and isolates other projects", () => {
    const storage = window.localStorage;
    storage.clear();

    const session = {
      ...createDefaultStudioSession("project-a"),
      currentMode: "storyboard" as const,
      currentView: "storyboard" as const,
      selectedShotId: "shot-1"
    };
    saveStudioSession(session, storage);

    expect(loadStudioSession("project-a", storage)).toMatchObject({
      currentMode: "storyboard",
      currentView: "storyboard",
      selectedShotId: "shot-1"
    });
    expect(loadStudioSession("project-b", storage).currentView).toBe("start");
  });

  it("falls back from corrupted or mismatched session data", () => {
    const storage = window.localStorage;
    storage.clear();
    storage.setItem(getStudioSessionStorageKey("project-a"), "{bad json");
    expect(loadStudioSession("project-a", storage).currentView).toBe("start");

    expect(
      normalizeStudioSession("project-a", {
        schemaVersion: 1,
        projectId: "other",
        currentView: "workflow"
      }).currentView
    ).toBe("start");
  });

  it("parses URL context and ignores invalid entity params safely", () => {
    expect(parseStudioUrlContext("?shotId=shot-1&intent=generate")).toMatchObject({
      selectedShotId: "shot-1",
      intent: "generate",
      ignored: false
    });
    expect(parseStudioUrlContext("?entityType=prop&entityId=x").ignored).toBe(true);
    expect(parseStudioUrlContext("?entityType=scene").ignored).toBe(true);
  });

  it("clears invalid selected ids after real data loads", () => {
    const session = {
      ...createDefaultStudioSession("project-a"),
      selectedShotId: "missing",
      selectedEntityType: "character" as const,
      selectedEntityId: "old-character"
    };

    expect(
      sanitizeStudioSessionSelection(session, {
        shotIds: new Set(["shot-1"]),
        characterIds: new Set(["character-1"]),
        sceneIds: new Set(["scene-1"])
      })
    ).toMatchObject({
      selectedShotId: null,
      selectedEntityType: null,
      selectedEntityId: null
    });
  });

  it("can clear the current project studio session", () => {
    const storage = window.localStorage;
    storage.clear();
    saveStudioSession(createDefaultStudioSession("project-a"), storage);
    expect(storage.getItem(getStudioSessionStorageKey("project-a"))).not.toBeNull();
    clearStudioSession("project-a", storage);
    expect(storage.getItem(getStudioSessionStorageKey("project-a"))).toBeNull();
  });
});
