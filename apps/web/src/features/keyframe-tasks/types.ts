import type { MediaAsset } from "@/features/characters/types";
import type {
  CharacterReferencePurpose,
  SceneReferencePurpose,
  ShotReferenceType
} from "@/features/shots/types";

export type KeyframeTaskStatus = "draft" | "ready";
export type KeyframeTaskPurpose = "first_frame" | "end_frame" | "concept" | "reference";
export type KeyframeTaskReadinessStatus = "incomplete" | "ready";
export type KeyframeTaskAspectRatio = "16:9" | "9:16" | "1:1" | "4:3" | "3:4" | "custom";
export type KeyframeTaskReferenceType = ShotReferenceType;
export type KeyframeTaskReferencePurpose = CharacterReferencePurpose | SceneReferencePurpose;

export type KeyframeTaskBlockingIssue =
  | "missing_name"
  | "no_prompt"
  | "invalid_dimensions"
  | "aspect_ratio_mismatch"
  | "invalid_steps"
  | "invalid_guidance"
  | "invalid_output_count"
  | "missing_primary_character_reference"
  | "missing_scene_reference"
  | "unavailable_media";

export type KeyframeTaskWarningIssue =
  | "no_english_prompt"
  | "no_negative_prompt"
  | "no_model_selected"
  | "shot_changed_since_snapshot"
  | "no_identity_reference"
  | "no_spatial_reference"
  | "no_seed"
  | "missing_secondary_character_reference";

export interface KeyframeShotSnapshotCharacter {
  shot_character_id: string;
  character_id: string;
  character_name: string;
  look_id: string | null;
  look_name: string | null;
  action_description: string | null;
  expression_description: string | null;
  position_description: string | null;
  is_primary_subject: boolean;
  order_index: number;
}

export interface KeyframeShotSnapshot {
  schema_version: 1;
  shot_id: string;
  order_index: number;
  title: string;
  story_description: string | null;
  visual_description: string | null;
  action_summary: string | null;
  dialogue: string | null;
  mood_description: string | null;
  duration_seconds: number | null;
  shot_scale: string;
  camera_angle: string;
  custom_camera_angle: string | null;
  camera_height: string;
  custom_camera_height: string | null;
  lens: string | null;
  composition_type: string;
  custom_composition: string | null;
  camera_movement: string;
  custom_camera_movement: string | null;
  scene_id: string | null;
  scene_name: string | null;
  scene_state_id: string | null;
  scene_state_name: string | null;
  characters: KeyframeShotSnapshotCharacter[];
}

export interface KeyframeTaskReadiness {
  readiness_status: KeyframeTaskReadinessStatus;
  blocking_issues: KeyframeTaskBlockingIssue[];
  warnings: KeyframeTaskWarningIssue[];
}

export interface KeyframeTaskReference {
  id: string;
  task_id: string;
  reference_type: KeyframeTaskReferenceType;
  shot_reference_id: string | null;
  character_reference_id: string | null;
  scene_reference_id: string | null;
  media_asset_id: string;
  purpose: KeyframeTaskReferencePurpose;
  order_index: number;
  source_shot_character_id: string | null;
  source_character_id: string | null;
  source_look_id: string | null;
  source_scene_id: string | null;
  source_scene_state_id: string | null;
  source_reference_deleted: boolean;
  media_asset: MediaAsset | null;
  created_at: string;
}

export interface KeyframeTask {
  id: string;
  project_id: string;
  shot_id: string;
  name: string;
  purpose: KeyframeTaskPurpose;
  status: KeyframeTaskStatus;
  shot_snapshot: KeyframeShotSnapshot;
  source_shot_updated_at: string;
  prompt_zh: string | null;
  prompt_en: string | null;
  negative_prompt: string | null;
  aspect_ratio: KeyframeTaskAspectRatio;
  width: number;
  height: number;
  seed: number | null;
  steps: number;
  guidance_scale: number;
  sampler_name: string | null;
  scheduler_name: string | null;
  model_provider: string | null;
  model_name: string | null;
  model_version: string | null;
  output_count: number;
  readiness: KeyframeTaskReadiness;
  shot_changed_since_snapshot: boolean;
  references: KeyframeTaskReference[];
  reference_count: number;
  created_at: string;
  updated_at: string;
}

export interface KeyframeTaskListResponse {
  items: KeyframeTask[];
  total: number;
}

export interface KeyframeTaskReferenceListResponse {
  items: KeyframeTaskReference[];
  total: number;
}

export interface KeyframeTaskCreateInput {
  name?: string | null;
  purpose?: KeyframeTaskPurpose;
  copy_current_references?: boolean;
}

export interface KeyframeTaskUpdateInput {
  name?: string | null;
  purpose?: KeyframeTaskPurpose;
  prompt_zh?: string | null;
  prompt_en?: string | null;
  negative_prompt?: string | null;
  aspect_ratio?: KeyframeTaskAspectRatio;
  width?: number;
  height?: number;
  seed?: number | null;
  steps?: number;
  guidance_scale?: number;
  sampler_name?: string | null;
  scheduler_name?: string | null;
  model_provider?: string | null;
  model_name?: string | null;
  model_version?: string | null;
  output_count?: number;
}

export interface KeyframeTaskReferenceCreateInput {
  shot_reference_id: string;
  purpose?: KeyframeTaskReferencePurpose | null;
}

export interface KeyframeTaskReferenceUpdateInput {
  purpose?: KeyframeTaskReferencePurpose | null;
  order_index?: number;
}
