import type { CharacterReference, MediaAsset } from "@/features/characters/types";
import type { SceneReference } from "@/features/scenes/types";

export type ShotScale =
  | "extreme_wide"
  | "wide"
  | "full"
  | "medium_wide"
  | "medium"
  | "medium_close"
  | "close"
  | "close_up"
  | "extreme_close_up"
  | "unknown";
export type CameraHeight =
  | "ground"
  | "low"
  | "eye_level"
  | "high"
  | "overhead"
  | "aerial"
  | "custom"
  | "unknown";
export type CameraAngle =
  | "front"
  | "back"
  | "left_profile"
  | "right_profile"
  | "left_three_quarter"
  | "right_three_quarter"
  | "top_down"
  | "dutch_angle"
  | "pov"
  | "over_the_shoulder"
  | "custom"
  | "unknown";
export type ShotCompositionType =
  | "centered"
  | "symmetrical"
  | "rule_of_thirds"
  | "leading_lines"
  | "frame_within_frame"
  | "layered"
  | "negative_space"
  | "close_blocking"
  | "custom"
  | "unknown";
export type CameraMovement =
  | "static"
  | "push_in"
  | "pull_out"
  | "pan_left"
  | "pan_right"
  | "tilt_up"
  | "tilt_down"
  | "tracking"
  | "orbit"
  | "handheld"
  | "crane"
  | "zoom_in"
  | "zoom_out"
  | "custom"
  | "unknown";

export type ReadinessStatus = "draft" | "basic_ready" | "asset_ready";
export type MissingItem =
  | "visual_description"
  | "scene"
  | "scene_state"
  | "characters"
  | "primary_subject"
  | "character_references"
  | "scene_references";
export type ShotReferenceType = "character" | "scene";
export type CharacterReferencePurpose =
  | "identity"
  | "appearance"
  | "expression"
  | "pose"
  | "framing"
  | "general";
export type SceneReferencePurpose =
  | "environment"
  | "spatial"
  | "composition"
  | "lighting"
  | "camera_reference"
  | "general";

export interface ShotSceneSummary {
  id: string;
  name: string;
}

export interface ShotCharacter {
  id: string;
  shot_id: string;
  character_id: string;
  character_name: string;
  look_id: string | null;
  look_name: string | null;
  action_description: string | null;
  expression_description: string | null;
  position_description: string | null;
  is_primary_subject: boolean;
  order_index: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShotReference {
  id: string;
  shot_id: string;
  reference_type: ShotReferenceType;
  character_reference_id: string | null;
  scene_reference_id: string | null;
  shot_character_id: string | null;
  purpose: string;
  order_index: number;
  notes: string | null;
  media_asset: MediaAsset | null;
  character_reference: CharacterReference | null;
  scene_reference: SceneReference | null;
  created_at: string;
  updated_at: string;
}

export interface Shot {
  id: string;
  project_id: string;
  name: string;
  order_index: number;
  story_description: string | null;
  visual_description: string | null;
  dialogue: string | null;
  action_summary: string | null;
  duration_seconds: number | null;
  shot_scale: ShotScale;
  camera_height: CameraHeight;
  custom_camera_height: string | null;
  camera_angle: CameraAngle;
  custom_camera_angle: string | null;
  composition_type: ShotCompositionType;
  custom_composition: string | null;
  camera_movement: CameraMovement;
  custom_camera_movement: string | null;
  focal_subject: string | null;
  mood_description: string | null;
  scene_id: string | null;
  scene_state_id: string | null;
  scene: ShotSceneSummary | null;
  scene_state: ShotSceneSummary | null;
  notes: string | null;
  readiness_status: ReadinessStatus;
  missing_items: MissingItem[];
  character_count: number;
  reference_count: number;
  characters: ShotCharacter[];
  references: ShotReference[];
  created_at: string;
  updated_at: string;
}

export interface ShotListResponse {
  items: Shot[];
  total: number;
}

export interface ShotCharacterListResponse {
  items: ShotCharacter[];
  total: number;
}

export interface ShotReferenceListResponse {
  items: ShotReference[];
  total: number;
}

export interface ShotInput {
  name: string;
  story_description?: string | null;
  visual_description?: string | null;
  dialogue?: string | null;
  action_summary?: string | null;
  duration_seconds?: number | null;
  shot_scale?: ShotScale;
  camera_height?: CameraHeight;
  custom_camera_height?: string | null;
  camera_angle?: CameraAngle;
  custom_camera_angle?: string | null;
  composition_type?: ShotCompositionType;
  custom_composition?: string | null;
  camera_movement?: CameraMovement;
  custom_camera_movement?: string | null;
  focal_subject?: string | null;
  mood_description?: string | null;
  scene_id?: string | null;
  scene_state_id?: string | null;
  notes?: string | null;
}

export type ShotUpdateInput = Partial<ShotInput>;

export interface ShotCharacterInput {
  character_id: string;
  look_id?: string | null;
  action_description?: string | null;
  expression_description?: string | null;
  position_description?: string | null;
  is_primary_subject?: boolean;
  notes?: string | null;
}

export type ShotCharacterUpdateInput = Partial<Omit<ShotCharacterInput, "character_id">>;

export interface ShotReferenceInput {
  reference_type: ShotReferenceType;
  character_reference_id?: string | null;
  scene_reference_id?: string | null;
  shot_character_id?: string | null;
  purpose: CharacterReferencePurpose | SceneReferencePurpose;
  notes?: string | null;
}

export interface ShotReferenceUpdateInput {
  purpose?: CharacterReferencePurpose | SceneReferencePurpose;
  notes?: string | null;
}
