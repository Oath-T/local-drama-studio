export type Sprint27CDestructiveAction =
  | "create_test_entity"
  | "delete"
  | "duplicate"
  | "reorder"
  | "bulk_modify"
  | "cleanup";

export interface E2EEntity {
  id: string;
  projectId: string;
  name: string;
  createdAt: string;
}

export interface Sprint27CE2ERunContext {
  projectId: string;
  projectName: string;
  runId: string;
  marker: string;
  startedAt: string;
  createdEntityIds: Set<string>;
  createdEntities: Map<string, E2EEntity>;
}

export const SPRINT_27C_E2E_PREFIX: string;
export const SPRINT_27C_PROTECTED_PROJECT_IDS: Set<string>;

export class Sprint27CE2ESafetyError extends Error {
  code: string;
  constructor(message: string, code: string);
}

export function createRunMarker(runId: string): string;
export function assertProjectActionAllowed(input: {
  projectId: string;
  projectName: string;
  action: Sprint27CDestructiveAction | string;
}): void;
export function createE2ERunContext(input: {
  projectId: string;
  projectName: string;
  runId: string;
  startedAt: string;
}): Sprint27CE2ERunContext;
export function registerCreatedEntity(
  context: Sprint27CE2ERunContext,
  entity: E2EEntity
): E2EEntity;
export function assertCleanupCandidate(
  context: Sprint27CE2ERunContext,
  entity: E2EEntity
): void;
export function cleanupCreatedEntities(
  context: Sprint27CE2ERunContext,
  entities: E2EEntity[],
  deleteEntity: (entity: E2EEntity) => Promise<void>
): Promise<string[]>;
