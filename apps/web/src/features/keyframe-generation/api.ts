import { apiDeleteJson, apiGet, apiPost } from "@/lib/api-client";

import type {
  KeyframeOutput,
  KeyframeRun,
  KeyframeRunCreateInput,
  KeyframeRunCreateResponse,
  KeyframeRunListResponse,
  KeyframeWorkflowListResponse,
  SystemCapabilities
} from "./types";

export function fetchSystemCapabilities(): Promise<SystemCapabilities> {
  return apiGet<SystemCapabilities>("/api/system/capabilities");
}

export function fetchKeyframeWorkflows(
  projectId: string
): Promise<KeyframeWorkflowListResponse> {
  return apiGet<KeyframeWorkflowListResponse>(`/api/projects/${projectId}/keyframe-workflows`);
}

export function startKeyframeRun(
  projectId: string,
  taskId: string,
  payload: KeyframeRunCreateInput
): Promise<KeyframeRunCreateResponse> {
  return apiPost<KeyframeRunCreateResponse, KeyframeRunCreateInput>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/runs`,
    payload
  );
}

export function fetchKeyframeRuns(
  projectId: string,
  taskId: string
): Promise<KeyframeRunListResponse> {
  return apiGet<KeyframeRunListResponse>(
    `/api/projects/${projectId}/keyframe-tasks/${taskId}/runs`
  );
}

export function fetchKeyframeRun(projectId: string, runId: string): Promise<KeyframeRun> {
  return apiGet<KeyframeRun>(`/api/projects/${projectId}/keyframe-runs/${runId}`);
}

export function retryKeyframeRun(
  projectId: string,
  runId: string
): Promise<KeyframeRunCreateResponse> {
  return apiPost<KeyframeRunCreateResponse, Record<string, never>>(
    `/api/projects/${projectId}/keyframe-runs/${runId}/retry`,
    {}
  );
}

export function selectKeyframeOutput(projectId: string, outputId: string): Promise<KeyframeOutput> {
  return apiPost<KeyframeOutput, Record<string, never>>(
    `/api/projects/${projectId}/keyframe-outputs/${outputId}/select`,
    {}
  );
}

export function unselectKeyframeOutput(
  projectId: string,
  outputId: string
): Promise<KeyframeOutput> {
  return apiDeleteJson<KeyframeOutput>(
    `/api/projects/${projectId}/keyframe-outputs/${outputId}/select`
  );
}
