import { apiPost } from "@/lib/api-client";

export type QuickGenerateMode = "first_frame" | "end_frame" | "video";
export type QuickGenerateRunType = "keyframe" | "video";

export interface WorkflowCapability {
  workflow_id: string;
  display_name: string;
  task_type: QuickGenerateRunType;
  supports: QuickGenerateMode[];
  requires: string[];
  recommended_for: string[];
  executable: boolean;
  missing_models: string[];
  missing_nodes: string[];
  missing_requirements: string[];
  quality_tier: "basic" | "standard" | "production";
  speed_tier: "fast" | "normal" | "slow";
  visual_only: boolean;
}

export interface WorkflowRoute {
  selected_workflow_id: string | null;
  executable: boolean;
  reason_zh: string;
  required_inputs: string[];
  missing_inputs: string[];
  missing_models: string[];
  missing_nodes: string[];
  warnings: string[];
  fallback: string | null;
}

export interface QuickGeneratePreviewInput {
  mode: QuickGenerateMode;
  prompt?: string | null;
  negative_prompt?: string | null;
  workflow_id?: string | null;
}

export interface QuickGeneratePreviewResponse {
  mode: QuickGenerateMode;
  route: WorkflowRoute;
  capabilities: WorkflowCapability[];
}

export interface QuickGenerateExecuteInput extends QuickGeneratePreviewInput {
  request_id: string;
}

export interface CanvasSyncResponse {
  attempted: boolean;
  synced: boolean;
  node_id: string | null;
  edge_id: string | null;
  error_message: string | null;
}

export interface QuickGenerateExecuteResponse {
  mode: QuickGenerateMode;
  run_type: QuickGenerateRunType;
  request_id: string;
  idempotent_replay: boolean;
  reused_active_run: boolean;
  task_id: string;
  run_id: string;
  status: string;
  workflow_id: string;
  route: WorkflowRoute;
  canvas_sync: CanvasSyncResponse;
}

export interface QuickGenerateSyncOutputInput {
  run_type: QuickGenerateRunType;
  run_id: string;
}

export const quickGenerateKeys = {
  preview: (projectId: string, shotId: string, mode: QuickGenerateMode, prompt: string) =>
    ["projects", projectId, "shots", shotId, "quick-generate", "preview", mode, prompt] as const
};

export function previewQuickGenerate(
  projectId: string,
  shotId: string,
  payload: QuickGeneratePreviewInput
): Promise<QuickGeneratePreviewResponse> {
  return apiPost<QuickGeneratePreviewResponse, QuickGeneratePreviewInput>(
    `/api/projects/${projectId}/shots/${shotId}/quick-generate/preview`,
    payload
  );
}

export function executeQuickGenerate(
  projectId: string,
  shotId: string,
  payload: QuickGenerateExecuteInput
): Promise<QuickGenerateExecuteResponse> {
  return apiPost<QuickGenerateExecuteResponse, QuickGenerateExecuteInput>(
    `/api/projects/${projectId}/shots/${shotId}/quick-generate`,
    payload
  );
}

export function syncQuickGenerateOutput(
  projectId: string,
  shotId: string,
  payload: QuickGenerateSyncOutputInput
): Promise<CanvasSyncResponse> {
  return apiPost<CanvasSyncResponse, QuickGenerateSyncOutputInput>(
    `/api/projects/${projectId}/shots/${shotId}/quick-generate/sync-output`,
    payload
  );
}
