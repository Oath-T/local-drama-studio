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
  it("persists only the simplified Studio state", () => {
    const storage = window.localStorage;
    storage.clear();

    saveStudioSession(
      {
        ...createDefaultStudioSession("project-a"),
        selectedShotId: "shot-1",
        scrollPosition: 240
      },
      storage
    );

    expect(loadStudioSession("project-a", storage)).toMatchObject({
      projectId: "project-a",
      selectedShotId: "shot-1",
      scrollPosition: 240
    });
    expect(loadStudioSession("project-b", storage).selectedShotId).toBeNull();
  });

  it("ignores old complex session fields while migrating selected shot", () => {
    expect(
      normalizeStudioSession("project-a", {
        schemaVersion: 2,
        projectId: "project-a",
        currentView: "storyboard",
        storyboardDensity: "large",
        selectedShotIds: ["shot-1", "shot-2"],
        selectedShotId: "shot-1"
      })
    ).toEqual(
      expect.objectContaining({
        schemaVersion: 3,
        projectId: "project-a",
        selectedShotId: "shot-1",
        scrollPosition: 0
      })
    );
  });

  it("falls back from corrupted or mismatched session data", () => {
    const storage = window.localStorage;
    storage.clear();
    storage.setItem(getStudioSessionStorageKey("project-a"), "{bad json");

    expect(loadStudioSession("project-a", storage).selectedShotId).toBeNull();
    expect(
      normalizeStudioSession("project-a", {
        schemaVersion: 3,
        projectId: "other",
        selectedShotId: "shot-1"
      }).selectedShotId
    ).toBeNull();
  });

  it("parses shot URL context and flags removed entity params", () => {
    expect(parseStudioUrlContext("?shotId=shot-1&intent=generate")).toMatchObject({
      selectedShotId: "shot-1",
      intent: "generate",
      ignored: false
    });
    expect(parseStudioUrlContext("?entityType=scene&entityId=scene-1")).toMatchObject({
      selectedShotId: null,
      ignored: true
    });
  });

  it("clears missing shot selections after real data loads", () => {
    expect(
      sanitizeStudioSessionSelection(
        {
          ...createDefaultStudioSession("project-a"),
          selectedShotId: "missing"
        },
        new Set(["shot-1"])
      ).selectedShotId
    ).toBeNull();
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
