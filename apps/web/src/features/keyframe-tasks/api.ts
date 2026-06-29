import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api-client";
import { shotKeys } from "@/features/shots/api";

import type {
  KeyframeTask,
  KeyframeTaskCreateInput,
  KeyframeTaskListResponse,
  KeyframeTaskReferenceCreateInput,
  KeyframeTaskReferenceListResponse,
  KeyframeTaskReferenceUpdateInput,
  KeyframeTaskUpdateInput
} from "./types";

export { shotKeys as keyframeTaskKeys };

export function fetchKeyframeTasks(
  projectId: string,
  shotId: string
): Promise<KeyframeTaskListResponse> {
  return apiGet<KeyframeTaskListResponse>(
    `/api/projects/${projectId}/shots/${shotId}/keyframe-tasks`
  );
}

export function createKeyframeTask(
  projectId: string,
  shotId: string,
  payload: KeyframeTaskCreateInput
): Promise<KeyframeTask> {
  return apiPost<KeyframeTask, KeyframeTaskCreateInput>(
    `/api/projects/${projectId}/shots/${shotId}/keyframe-tasks`,
    payload
  );
}

export function fetchKeyframeTask(projectId: string, taskId: string): Promise<KeyframeTask> {
  return apiGet<KeyframeTask>(`/api/projects/${projectId}/keyframe-tasks/${taskId}`);
}

export function updateKeyframeTask(
  projectId: string,
  taskId: string,
  payload: KeyframeTaskUpdateInput
): Promise<KeyframeTask> {
  return apiPatch<KeyframeTask, KeyframeTaskUpdateInput>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}`,
    payload
  );
}

export function deleteKeyframeTask(projectId: string, taskId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/keyframe-tasks/${taskId}`);
}

export function duplicateKeyframeTask(projectId: string, taskId: string): Promise<KeyframeTask> {
  return apiPost<KeyframeTask, Record<string, never>>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/duplicate`,
    {}
  );
}

export function markKeyframeTaskReady(projectId: string, taskId: string): Promise<KeyframeTask> {
  return apiPost<KeyframeTask, Record<string, never>>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/mark-ready`,
    {}
  );
}

export function markKeyframeTaskDraft(projectId: string, taskId: string): Promise<KeyframeTask> {
  return apiPost<KeyframeTask, Record<string, never>>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/mark-draft`,
    {}
  );
}

export function fetchKeyframeTaskReferences(
  projectId: string,
  taskId: string
): Promise<KeyframeTaskReferenceListResponse> {
  return apiGet<KeyframeTaskReferenceListResponse>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/references`
  );
}

export function addKeyframeTaskReference(
  projectId: string,
  taskId: string,
  payload: KeyframeTaskReferenceCreateInput
): Promise<KeyframeTask> {
  return apiPost<KeyframeTask, KeyframeTaskReferenceCreateInput>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/references`,
    payload
  );
}

export function updateKeyframeTaskReference(
  projectId: string,
  taskId: string,
  taskReferenceId: string,
  payload: KeyframeTaskReferenceUpdateInput
): Promise<KeyframeTask> {
  return apiPatch<KeyframeTask, KeyframeTaskReferenceUpdateInput>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/references/${taskReferenceId}`,
    payload
  );
}

export function deleteKeyframeTaskReference(
  projectId: string,
  taskId: string,
  taskReferenceId: string
): Promise<void> {
  return apiDelete(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/references/${taskReferenceId}`
  );
}
