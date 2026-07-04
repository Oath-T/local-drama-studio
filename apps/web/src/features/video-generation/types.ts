import type { MediaAsset } from "@/features/characters/types";

export type VideoTaskStatus = "draft" | "ready";
export type VideoRunStatus = "queued" | "running" | "completed" | "failed" | "interrupted";
export type VideoTaskReadinessStatus = "ready" | "incomplete";
export type VideoTaskBlockingIssue =
  | "missing_name"
  | "missing_input_image"
  | "input_image_unavailable"
  | "input_image_not_image"
  | "missing_prompt"
  | "invalid_duration"
  | "invalid_fps"
  | "invalid_dimensions"
  | "invalid_seed"
  | "workflow_not_selected"
  | "workflow_unavailable";
export type VideoTaskWarning =
  | "no_negative_prompt"
  | "no_camera_motion"
  | "no_seed"
  | "low_resolution"
  | "high_estimated_runtime";

export interface VideoGenerationCapability {
  available: boolean;
  provider: string;
  status: "online" | "offline" | "unconfigured" | string;
}

export interface VideoTaskReadiness {
  readiness_status: VideoTaskReadinessStatus;
  blocking_issues: VideoTaskBlockingIssue[];
  warnings: VideoTaskWarning[];
}

export interface VideoOutput {
  id: string;
  project_id: string;
  run_id: string;
  media_asset_id: string;
  output_index: number;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  fps: number | null;
  seed: number | null;
  is_selected: boolean;
  media_asset: MediaAsset | null;
  created_at: string;
}

export interface VideoTask {
  id: string;
  project_id: string;
  shot_id: string;
  name: string;
  status: VideoTaskStatus;
  input_media_asset_id: string | null;
  source_keyframe_output_id: string | null;
  source_keyframe_task_id: string | null;
  prompt: string | null;
  negative_prompt: string | null;
  duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  seed: number | null;
  motion_strength: number | null;
  camera_motion: string | null;
  workflow_id: string | null;
  input_media_asset: MediaAsset | null;
  readiness: VideoTaskReadiness;
  latest_run_status: VideoRunStatus | null;
  selected_output: VideoOutput | null;
  created_at: string;
  updated_at: string;
}

export interface VideoTaskListResponse {
  items: VideoTask[];
  total: number;
}

export interface VideoTaskCreateInput {
  input_media_asset_id?: string | null;
  source_keyframe_output_id?: string | null;
  source_keyframe_task_id?: string | null;
}

export interface VideoTaskUpdateInput {
  name?: string | null;
  input_media_asset_id?: string | null;
  source_keyframe_output_id?: string | null;
  source_keyframe_task_id?: string | null;
  prompt?: string | null;
  negative_prompt?: string | null;
  duration_seconds?: number | null;
  fps?: number | null;
  width?: number | null;
  height?: number | null;
  seed?: number | null;
  motion_strength?: number | null;
  camera_motion?: string | null;
  workflow_id?: string | null;
}

export interface VideoWorkflow {
  workflow_id: string;
  display_name: string;
  version: string;
  available: boolean;
  missing_requirements: string[];
  reference_inputs_used: boolean;
}

export interface VideoWorkflowListResponse {
  items: VideoWorkflow[];
  total: number;
}

export interface VideoRunCreateInput {
  workflow_id: string;
}

export interface VideoRunCreateResponse {
  run_id: string;
  status: VideoRunStatus;
}

export interface VideoRunSnapshot {
  schema_version: 1;
  video_task_id: string;
  shot_id: string;
  workflow_id: string;
  workflow_version: string;
  input_media_asset_id: string;
  prompt: string;
  negative_prompt: string | null;
  duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  seed: number;
  motion_strength: number | null;
  camera_motion: string | null;
  reference_inputs_used: boolean;
}

export interface VideoRun {
  id: string;
  project_id: string;
  video_task_id: string;
  run_number: number;
  provider: string;
  workflow_id: string;
  workflow_version: string;
  status: VideoRunStatus;
  provider_job_id: string | null;
  submitted_payload_snapshot: VideoRunSnapshot;
  error_code: string | null;
  error_message_safe: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  outputs: VideoOutput[];
}

export interface VideoRunListResponse {
  items: VideoRun[];
  total: number;
}

export interface VideoInputUploadResponse {
  media_asset: MediaAsset;
}
