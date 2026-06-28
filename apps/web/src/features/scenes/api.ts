import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "@/lib/api-client";

import type {
  CameraPosition,
  CompositionType,
  Scene,
  SceneCreateInput,
  SceneListResponse,
  SceneReference,
  SceneReferenceListResponse,
  SceneReferenceUpdateInput,
  SceneState,
  SceneStateCreateInput,
  SceneStateListResponse,
  SceneStateUpdateInput,
  SceneUpdateInput,
  ShotScale,
  ViewDirection
} from "./types";

export const sceneKeys = {
  all: (projectId: string) => ["projects", projectId, "scenes"] as const,
  lists: (projectId: string) => [...sceneKeys.all(projectId), "list"] as const,
  detail: (projectId: string, sceneId: string) =>
    [...sceneKeys.all(projectId), "detail", sceneId] as const,
  states: (projectId: string, sceneId: string) =>
    [...sceneKeys.detail(projectId, sceneId), "states"] as const,
  references: (projectId: string, sceneId: string, stateId: string) =>
    [...sceneKeys.states(projectId, sceneId), stateId, "references"] as const
};

export function fetchScenes(projectId: string): Promise<SceneListResponse> {
  return apiGet<SceneListResponse>(`/api/projects/${projectId}/scenes`);
}

export function createScene(projectId: string, payload: SceneCreateInput): Promise<Scene> {
  return apiPost<Scene, SceneCreateInput>(`/api/projects/${projectId}/scenes`, payload);
}

export function fetchScene(projectId: string, sceneId: string): Promise<Scene> {
  return apiGet<Scene>(`/api/projects/${projectId}/scenes/${sceneId}`);
}

export function updateScene(
  projectId: string,
  sceneId: string,
  payload: SceneUpdateInput
): Promise<Scene> {
  return apiPatch<Scene, SceneUpdateInput>(`/api/projects/${projectId}/scenes/${sceneId}`, payload);
}

export function deleteScene(projectId: string, sceneId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/scenes/${sceneId}`);
}

export function fetchSceneStates(
  projectId: string,
  sceneId: string
): Promise<SceneStateListResponse> {
  return apiGet<SceneStateListResponse>(`/api/projects/${projectId}/scenes/${sceneId}/states`);
}

export function createSceneState(
  projectId: string,
  sceneId: string,
  payload: SceneStateCreateInput
): Promise<SceneState> {
  return apiPost<SceneState, SceneStateCreateInput>(
    `/api/projects/${projectId}/scenes/${sceneId}/states`,
    payload
  );
}

export function updateSceneState(
  projectId: string,
  sceneId: string,
  stateId: string,
  payload: SceneStateUpdateInput
): Promise<SceneState> {
  return apiPatch<SceneState, SceneStateUpdateInput>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}`,
    payload
  );
}

export function setDefaultSceneState(
  projectId: string,
  sceneId: string,
  stateId: string
): Promise<SceneState> {
  return apiPost<SceneState, Record<string, never>>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/set-default`,
    {}
  );
}

export function deleteSceneState(
  projectId: string,
  sceneId: string,
  stateId: string
): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}`);
}

export function fetchSceneReferences(
  projectId: string,
  sceneId: string,
  stateId: string
): Promise<SceneReferenceListResponse> {
  return apiGet<SceneReferenceListResponse>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references`
  );
}

export interface UploadSceneReferenceInput {
  file: File;
  shot_scale: ShotScale;
  camera_position: CameraPosition;
  custom_camera_position: string;
  view_direction: ViewDirection;
  custom_view_direction: string;
  composition_type: CompositionType;
  custom_composition: string;
  is_empty_plate: boolean;
  is_spatial_anchor: boolean;
  tags: string;
  description: string;
  notes: string;
}

export function uploadSceneReference(
  projectId: string,
  sceneId: string,
  stateId: string,
  input: UploadSceneReferenceInput
): Promise<SceneReference> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("shot_scale", input.shot_scale);
  formData.append("camera_position", input.camera_position);
  formData.append("custom_camera_position", input.custom_camera_position);
  formData.append("view_direction", input.view_direction);
  formData.append("custom_view_direction", input.custom_view_direction);
  formData.append("composition_type", input.composition_type);
  formData.append("custom_composition", input.custom_composition);
  formData.append("is_empty_plate", String(input.is_empty_plate));
  formData.append("is_spatial_anchor", String(input.is_spatial_anchor));
  formData.append("tags", input.tags);
  formData.append("description", input.description);
  formData.append("notes", input.notes);

  return apiPostForm<SceneReference>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references`,
    formData
  );
}

export function updateSceneReference(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string,
  payload: SceneReferenceUpdateInput
): Promise<SceneReference> {
  return apiPatch<SceneReference, SceneReferenceUpdateInput>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}`,
    payload
  );
}

export function setPrimarySceneReference(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string
): Promise<SceneReference> {
  return apiPost<SceneReference, Record<string, never>>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}/set-primary`,
    {}
  );
}

export function deleteSceneReference(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string
): Promise<void> {
  return apiDelete(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}`
  );
}
