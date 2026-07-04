import { apiDelete, apiDeleteJson, apiGet, apiPatch, apiPost, apiPostForm } from "@/lib/api-client";

import type {
  VideoInputUploadResponse,
  VideoOutput,
  VideoRun,
  VideoRunCreateInput,
  VideoRunCreateResponse,
  VideoRunListResponse,
  VideoTask,
  VideoTaskCreateInput,
  VideoTaskListResponse,
  VideoTaskUpdateInput,
  VideoWorkflowListResponse
} from "./types";

export function fetchVideoWorkflows(projectId: string): Promise<VideoWorkflowListResponse> {
  return apiGet<VideoWorkflowListResponse>(`/api/projects/${projectId}/video-workflows`);
}

export function fetchVideoTasks(projectId: string, shotId: string): Promise<VideoTaskListResponse> {
  return apiGet<VideoTaskListResponse>(`/api/projects/${projectId}/shots/${shotId}/video-tasks`);
}

export function createVideoTask(
  projectId: string,
  shotId: string,
  payload: VideoTaskCreateInput
): Promise<VideoTask> {
  return apiPost<VideoTask, VideoTaskCreateInput>(
    `/api/projects/${projectId}/shots/${shotId}/video-tasks`,
    payload
  );
}

export function updateVideoTask(
  projectId: string,
  taskId: string,
  payload: VideoTaskUpdateInput
): Promise<VideoTask> {
  return apiPatch<VideoTask, VideoTaskUpdateInput>(
    `/api/projects/${projectId}/video-tasks/${taskId}`,
    payload
  );
}

export function deleteVideoTask(projectId: string, taskId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/video-tasks/${taskId}`);
}

export function markVideoTaskReady(projectId: string, taskId: string): Promise<VideoTask> {
  return apiPost<VideoTask, Record<string, never>>(
    `/api/projects/${projectId}/video-tasks/${taskId}/mark-ready`,
    {}
  );
}

export function markVideoTaskDraft(projectId: string, taskId: string): Promise<VideoTask> {
  return apiPost<VideoTask, Record<string, never>>(
    `/api/projects/${projectId}/video-tasks/${taskId}/mark-draft`,
    {}
  );
}

export function startVideoRun(
  projectId: string,
  taskId: string,
  payload: VideoRunCreateInput
): Promise<VideoRunCreateResponse> {
  return apiPost<VideoRunCreateResponse, VideoRunCreateInput>(
    `/api/projects/${projectId}/video-tasks/${taskId}/runs`,
    payload
  );
}

export function fetchVideoRuns(projectId: string, taskId: string): Promise<VideoRunListResponse> {
  return apiGet<VideoRunListResponse>(`/api/projects/${projectId}/video-tasks/${taskId}/runs`);
}

export function fetchVideoRun(projectId: string, runId: string): Promise<VideoRun> {
  return apiGet<VideoRun>(`/api/projects/${projectId}/video-runs/${runId}`);
}

export function selectVideoOutput(projectId: string, outputId: string): Promise<VideoOutput> {
  return apiPost<VideoOutput, Record<string, never>>(
    `/api/projects/${projectId}/video-outputs/${outputId}/select`,
    {}
  );
}

export function unselectVideoOutput(projectId: string, outputId: string): Promise<VideoOutput> {
  return apiDeleteJson<VideoOutput>(`/api/projects/${projectId}/video-outputs/${outputId}/select`);
}

export function uploadVideoInputImage(
  projectId: string,
  file: File
): Promise<VideoInputUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPostForm<VideoInputUploadResponse>(
    `/api/projects/${projectId}/video-inputs/images`,
    formData
  );
}
