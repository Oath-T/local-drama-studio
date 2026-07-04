import type { MediaAsset } from "@/features/characters/types";

export type KeyframeRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface KeyframeGenerationCapability {
  available: boolean;
  provider: string;
  status: "online" | "offline" | "unconfigured" | string;
}

export interface SystemCapabilities {
  vision_analysis: {
    available: boolean;
    provider: string;
  };
  keyframe_generation: KeyframeGenerationCapability | null;
}

export interface KeyframeWorkflow {
  workflow_id: string;
  display_name: string;
  version: string;
  available: boolean;
  missing_requirements: string[];
  uses_reference_inputs: boolean;
}

export interface KeyframeWorkflowListResponse {
  items: KeyframeWorkflow[];
  total: number;
}

export interface KeyframeRunSnapshot {
  schema_version: 1;
  task_id: string;
  task_updated_at: string;
  workflow_id: string;
  workflow_version: string;
  prompt_zh: string | null;
  prompt_en: string | null;
  effective_prompt_language: "zh" | "en";
  effective_positive_prompt: string;
  negative_prompt: string | null;
  width: number;
  height: number;
  seed: number;
  steps: number;
  guidance_scale: number;
  sampler_name: string;
  scheduler_name: string;
  output_count: number;
  task_reference_ids: string[];
  media_asset_ids: string[];
  reference_inputs_used: boolean;
}

export interface KeyframeOutput {
  id: string;
  project_id: string;
  run_id: string;
  media_asset_id: string;
  output_index: number;
  width: number | null;
  height: number | null;
  seed: number | null;
  is_selected: boolean;
  media_asset: MediaAsset | null;
  created_at: string;
}

export interface KeyframeRun {
  id: string;
  project_id: string;
  keyframe_task_id: string;
  run_number: number;
  provider: string;
  workflow_id: string;
  workflow_version: string;
  status: KeyframeRunStatus;
  provider_job_id: string | null;
  submitted_payload_snapshot: KeyframeRunSnapshot;
  error_code: string | null;
  error_message_safe: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  outputs: KeyframeOutput[];
}

export interface KeyframeRunListResponse {
  items: KeyframeRun[];
  total: number;
}

export interface KeyframeRunCreateInput {
  workflow_id: string;
}

export interface KeyframeRunCreateResponse {
  run_id: string;
  status: KeyframeRunStatus;
}
