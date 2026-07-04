import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api-client";

import type {
  Shot,
  ShotCharacter,
  ShotCharacterInput,
  ShotCharacterListResponse,
  ShotCharacterUpdateInput,
  ShotInput,
  ShotListResponse,
  ShotRecommendationResponse,
  ShotReference,
  ShotReferenceInput,
  ShotReferenceListResponse,
  ShotReferenceUpdateInput,
  ShotUpdateInput
} from "./types";

export const shotKeys = {
  all: (projectId: string) => ["projects", projectId, "shots"] as const,
  lists: (projectId: string) => [...shotKeys.all(projectId), "list"] as const,
  detail: (projectId: string, shotId: string) =>
    [...shotKeys.all(projectId), "detail", shotId] as const,
  characters: (projectId: string, shotId: string) =>
    [...shotKeys.detail(projectId, shotId), "characters"] as const,
  references: (projectId: string, shotId: string) =>
    [...shotKeys.detail(projectId, shotId), "references"] as const,
  recommendations: (projectId: string, shotId: string) =>
    [...shotKeys.detail(projectId, shotId), "recommendations"] as const,
  keyframeTasks: (projectId: string, shotId: string) =>
    [...shotKeys.detail(projectId, shotId), "keyframe-tasks"] as const,
  keyframeTask: (projectId: string, taskId: string) =>
    [...shotKeys.all(projectId), "keyframe-task", taskId] as const,
  keyframeTaskReferences: (projectId: string, taskId: string) =>
    [...shotKeys.keyframeTask(projectId, taskId), "references"] as const,
  keyframeWorkflows: (projectId: string) =>
    ["projects", projectId, "keyframe-workflows"] as const,
  keyframeRuns: (projectId: string, taskId: string) =>
    [...shotKeys.keyframeTask(projectId, taskId), "runs"] as const,
  keyframeRun: (projectId: string, runId: string) =>
    [...shotKeys.all(projectId), "keyframe-run", runId] as const,
  systemCapabilities: () => ["system", "capabilities"] as const
};

export function fetchShots(projectId: string): Promise<ShotListResponse> {
  return apiGet<ShotListResponse>(`/api/projects/${projectId}/shots`);
}

export function createShot(projectId: string, payload: ShotInput): Promise<Shot> {
  return apiPost<Shot, ShotInput>(`/api/projects/${projectId}/shots`, payload);
}

export function fetchShot(projectId: string, shotId: string): Promise<Shot> {
  return apiGet<Shot>(`/api/projects/${projectId}/shots/${shotId}`);
}

export function updateShot(
  projectId: string,
  shotId: string,
  payload: ShotUpdateInput
): Promise<Shot> {
  return apiPatch<Shot, ShotUpdateInput>(`/api/projects/${projectId}/shots/${shotId}`, payload);
}

export function deleteShot(projectId: string, shotId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/shots/${shotId}`);
}

export function moveShot(projectId: string, shotId: string, orderIndex: number): Promise<Shot> {
  return apiPost<Shot, { order_index: number }>(
    `/api/projects/${projectId}/shots/${shotId}/move`,
    { order_index: orderIndex }
  );
}

export function duplicateShot(projectId: string, shotId: string): Promise<Shot> {
  return apiPost<Shot, Record<string, never>>(
    `/api/projects/${projectId}/shots/${shotId}/duplicate`,
    {}
  );
}

export function fetchShotCharacters(
  projectId: string,
  shotId: string
): Promise<ShotCharacterListResponse> {
  return apiGet<ShotCharacterListResponse>(
    `/api/projects/${projectId}/shots/${shotId}/characters`
  );
}

export function addShotCharacter(
  projectId: string,
  shotId: string,
  payload: ShotCharacterInput
): Promise<ShotCharacter> {
  return apiPost<ShotCharacter, ShotCharacterInput>(
    `/api/projects/${projectId}/shots/${shotId}/characters`,
    payload
  );
}

export function updateShotCharacter(
  projectId: string,
  shotId: string,
  shotCharacterId: string,
  payload: ShotCharacterUpdateInput
): Promise<ShotCharacter> {
  return apiPatch<ShotCharacter, ShotCharacterUpdateInput>(
    `/api/projects/${projectId}/shots/${shotId}/characters/${shotCharacterId}`,
    payload
  );
}

export function deleteShotCharacter(
  projectId: string,
  shotId: string,
  shotCharacterId: string
): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/shots/${shotId}/characters/${shotCharacterId}`);
}

export function moveShotCharacter(
  projectId: string,
  shotId: string,
  shotCharacterId: string,
  orderIndex: number
): Promise<ShotCharacter> {
  return apiPost<ShotCharacter, { order_index: number }>(
    `/api/projects/${projectId}/shots/${shotId}/characters/${shotCharacterId}/move`,
    { order_index: orderIndex }
  );
}

export function fetchShotReferences(
  projectId: string,
  shotId: string
): Promise<ShotReferenceListResponse> {
  return apiGet<ShotReferenceListResponse>(
    `/api/projects/${projectId}/shots/${shotId}/references`
  );
}

export function fetchShotRecommendations(
  projectId: string,
  shotId: string,
  limit = 5
): Promise<ShotRecommendationResponse> {
  return apiGet<ShotRecommendationResponse>(
    `/api/projects/${projectId}/shots/${shotId}/recommendations?limit=${limit}`
  );
}

export function addShotReference(
  projectId: string,
  shotId: string,
  payload: ShotReferenceInput
): Promise<ShotReference> {
  return apiPost<ShotReference, ShotReferenceInput>(
    `/api/projects/${projectId}/shots/${shotId}/references`,
    payload
  );
}

export function updateShotReference(
  projectId: string,
  shotId: string,
  shotReferenceId: string,
  payload: ShotReferenceUpdateInput
): Promise<ShotReference> {
  return apiPatch<ShotReference, ShotReferenceUpdateInput>(
    `/api/projects/${projectId}/shots/${shotId}/references/${shotReferenceId}`,
    payload
  );
}

export function deleteShotReference(
  projectId: string,
  shotId: string,
  shotReferenceId: string
): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/shots/${shotId}/references/${shotReferenceId}`);
}

export function moveShotReference(
  projectId: string,
  shotId: string,
  shotReferenceId: string,
  orderIndex: number
): Promise<ShotReference> {
  return apiPost<ShotReference, { order_index: number }>(
    `/api/projects/${projectId}/shots/${shotId}/references/${shotReferenceId}/move`,
    { order_index: orderIndex }
  );
}
