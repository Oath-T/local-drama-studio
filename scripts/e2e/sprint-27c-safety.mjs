export const SPRINT_27C_E2E_PREFIX = "E2E_SPRINT_27C";

export const SPRINT_27C_PROTECTED_PROJECT_IDS = new Set([
  "8c6200f3-23b0-4af5-a4db-6a2bd9cd6702"
]);

const destructiveActions = new Set([
  "create_test_entity",
  "delete",
  "duplicate",
  "reorder",
  "bulk_modify",
  "cleanup"
]);

export class Sprint27CE2ESafetyError extends Error {
  constructor(message, code) {
    super(message);
    this.name = "Sprint27CE2ESafetyError";
    this.code = code;
  }
}

export function createRunMarker(runId) {
  const normalizedRunId = String(runId ?? "").trim();
  if (!normalizedRunId) {
    throw new Sprint27CE2ESafetyError("E2E run ID is required.", "RUN_ID_REQUIRED");
  }
  return `[${SPRINT_27C_E2E_PREFIX}:${normalizedRunId}]`;
}

export function assertProjectActionAllowed({ projectId, projectName, action }) {
  if (!destructiveActions.has(action)) {
    return;
  }
  if (SPRINT_27C_PROTECTED_PROJECT_IDS.has(projectId)) {
    throw new Sprint27CE2ESafetyError(
      "Protected real project cannot run destructive browser validation.",
      "REAL_PROJECT_WRITE_FORBIDDEN"
    );
  }
  if (!String(projectName ?? "").startsWith(SPRINT_27C_E2E_PREFIX)) {
    throw new Sprint27CE2ESafetyError(
      "Destructive browser validation requires the dedicated Sprint 27C E2E project.",
      "E2E_PROJECT_REQUIRED"
    );
  }
}

export function createE2ERunContext({ projectId, projectName, runId, startedAt }) {
  assertProjectActionAllowed({ projectId, projectName, action: "create_test_entity" });
  const marker = createRunMarker(runId);
  const startTime = new Date(startedAt);
  if (Number.isNaN(startTime.getTime())) {
    throw new Sprint27CE2ESafetyError("E2E run start time is invalid.", "RUN_START_INVALID");
  }
  return {
    projectId,
    projectName,
    runId,
    marker,
    startedAt: startTime.toISOString(),
    createdEntityIds: new Set(),
    createdEntities: new Map()
  };
}

export function registerCreatedEntity(context, entity) {
  assertCleanupCandidateShape(context, entity, false);
  context.createdEntityIds.add(entity.id);
  context.createdEntities.set(entity.id, { ...entity });
  return entity;
}

function assertCleanupCandidateShape(context, entity, requireRegistered) {
  assertProjectActionAllowed({
    projectId: context.projectId,
    projectName: context.projectName,
    action: "cleanup"
  });
  if (entity.projectId !== context.projectId) {
    throw new Sprint27CE2ESafetyError(
      "Cleanup entity does not belong to this E2E project.",
      "ENTITY_PROJECT_MISMATCH"
    );
  }
  if (requireRegistered && !context.createdEntityIds.has(entity.id)) {
    throw new Sprint27CE2ESafetyError(
      "Cleanup entity was not created by this E2E run.",
      "ENTITY_NOT_CREATED_BY_RUN"
    );
  }
  if (!String(entity.name ?? "").includes(context.marker)) {
    throw new Sprint27CE2ESafetyError(
      "Cleanup entity is missing the current E2E run marker.",
      "ENTITY_MARKER_MISSING"
    );
  }
  const createdAt = new Date(entity.createdAt);
  if (Number.isNaN(createdAt.getTime()) || createdAt < new Date(context.startedAt)) {
    throw new Sprint27CE2ESafetyError(
      "Cleanup entity predates the current E2E run.",
      "ENTITY_PREDATES_RUN"
    );
  }
}

export function assertCleanupCandidate(context, entity) {
  assertCleanupCandidateShape(context, entity, true);
}

export async function cleanupCreatedEntities(context, entities, deleteEntity) {
  for (const entity of entities) {
    assertCleanupCandidate(context, entity);
  }

  const deletedEntityIds = [];
  for (const entity of entities) {
    await deleteEntity(entity);
    deletedEntityIds.push(entity.id);
  }
  return deletedEntityIds;
}
