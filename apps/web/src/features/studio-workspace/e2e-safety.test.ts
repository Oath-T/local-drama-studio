import { describe, expect, it, vi } from "vitest";

import {
  assertCleanupCandidate,
  assertProjectActionAllowed,
  cleanupCreatedEntities,
  createE2ERunContext,
  registerCreatedEntity,
  Sprint27CE2ESafetyError
} from "../../../../../scripts/e2e/sprint-27c-safety.mjs";

const realProjectId = "8c6200f3-23b0-4af5-a4db-6a2bd9cd6702";
const e2eProjectId = "e2e-project-id";
const startedAt = "2026-07-19T06:00:00.000Z";

function createContext(runId = "run-current") {
  return createE2ERunContext({
    projectId: e2eProjectId,
    projectName: "E2E_SPRINT_27C",
    runId,
    startedAt
  });
}

function entity(overrides: Partial<{ id: string; projectId: string; name: string; createdAt: string }> = {}) {
  return {
    id: "shot-current",
    projectId: e2eProjectId,
    name: "[E2E_SPRINT_27C:run-current] 镜头",
    createdAt: "2026-07-19T06:00:01.000Z",
    ...overrides
  };
}

describe("Sprint 27C E2E safety guard", () => {
  it("rejects DELETE against the protected real project", () => {
    expect(() =>
      assertProjectActionAllowed({
        projectId: realProjectId,
        projectName: "真实项目",
        action: "delete"
      })
    ).toThrowError(expect.objectContaining({ code: "REAL_PROJECT_WRITE_FORBIDDEN" }));
  });

  it("rejects cleanup outside the dedicated E2E project", () => {
    expect(() =>
      createE2ERunContext({
        projectId: "ordinary-project",
        projectName: "普通项目",
        runId: "run-current",
        startedAt
      })
    ).toThrowError(expect.objectContaining({ code: "E2E_PROJECT_REQUIRED" }));
  });

  it("rejects an entity not registered in createdEntityIds", () => {
    expect(() => assertCleanupCandidate(createContext(), entity())).toThrowError(
      expect.objectContaining({ code: "ENTITY_NOT_CREATED_BY_RUN" })
    );
  });

  it("rejects an entity created by an older run", () => {
    const context = createContext();
    const candidate = entity({
      id: "shot-old",
      name: "[E2E_SPRINT_27C:run-old] 镜头"
    });
    context.createdEntityIds.add(candidate.id);

    expect(() => assertCleanupCandidate(context, candidate)).toThrowError(
      expect.objectContaining({ code: "ENTITY_MARKER_MISSING" })
    );
  });

  it("rejects an entity without the current run marker", () => {
    const context = createContext();
    const candidate = entity({ name: "没有测试标识的镜头" });
    context.createdEntityIds.add(candidate.id);

    expect(() => assertCleanupCandidate(context, candidate)).toThrowError(
      expect.objectContaining({ code: "ENTITY_MARKER_MISSING" })
    );
  });

  it("allows cleanup of an entity created and registered by the current run", async () => {
    const context = createContext();
    const candidate = entity();
    registerCreatedEntity(context, candidate);
    const deleteEntity = vi.fn().mockResolvedValue(undefined);

    await expect(cleanupCreatedEntities(context, [candidate], deleteEntity)).resolves.toEqual([
      candidate.id
    ]);
    expect(deleteEntity).toHaveBeenCalledOnce();
  });

  it("validates every candidate before deleting and stops on cleanup failure", async () => {
    const context = createContext();
    const first = entity({ id: "shot-first" });
    const unknown = entity({ id: "shot-unknown" });
    registerCreatedEntity(context, first);
    const deleteEntity = vi.fn().mockResolvedValue(undefined);

    await expect(cleanupCreatedEntities(context, [first, unknown], deleteEntity)).rejects.toBeInstanceOf(
      Sprint27CE2ESafetyError
    );
    expect(deleteEntity).not.toHaveBeenCalled();

    const second = entity({ id: "shot-second" });
    registerCreatedEntity(context, second);
    deleteEntity.mockRejectedValueOnce(new Error("cleanup failed"));
    await expect(cleanupCreatedEntities(context, [first, second], deleteEntity)).rejects.toThrow(
      "cleanup failed"
    );
    expect(deleteEntity).toHaveBeenCalledTimes(1);
  });
});
