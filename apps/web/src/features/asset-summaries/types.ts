import type { MediaAsset } from "@/features/characters/types";

export interface SummaryReference {
  id: string;
  reference_type: "character" | "scene";
  label: string;
  purpose: string | null;
  look_id: string | null;
  look_name: string | null;
  state_id: string | null;
  state_name: string | null;
  is_primary: boolean;
  is_identity_anchor: boolean;
  is_spatial_anchor: boolean;
  is_empty_plate: boolean;
  media_asset: Pick<
    MediaAsset,
    | "id"
    | "media_type"
    | "original_filename"
    | "mime_type"
    | "width"
    | "height"
    | "thumbnail_url"
    | "content_url"
    | "created_at"
  > | null;
  created_at: string;
}

export interface RecentShotSummary {
  id: string;
  name: string;
  order_index: number;
  updated_at: string;
}

export interface CharacterAssetSummary {
  id: string;
  project_id: string;
  name: string;
  default_look_id: string | null;
  default_look_name: string | null;
  look_count: number;
  reference_count: number;
  primary_reference_count: number;
  identity_anchor_count: number;
  face_reference_count: number;
  full_body_reference_count: number;
  used_shot_count: number;
  recent_shots: RecentShotSummary[];
  featured_references: SummaryReference[];
  completeness_warnings: string[];
}

export interface SceneAssetSummary {
  id: string;
  project_id: string;
  name: string;
  default_state_id: string | null;
  default_state_name: string | null;
  state_count: number;
  reference_count: number;
  primary_reference_count: number;
  spatial_anchor_count: number;
  empty_plate_count: number;
  wide_reference_count: number;
  used_shot_count: number;
  recent_shots: RecentShotSummary[];
  featured_references: SummaryReference[];
  completeness_warnings: string[];
}

export interface ShotAssetCharacterSummary {
  shot_character_id: string;
  character_id: string;
  character_name: string;
  look_id: string | null;
  look_name: string | null;
  is_primary_subject: boolean;
  bound_reference_count: number;
  completeness_warnings: string[];
}

export interface ShotAssetSceneSummary {
  scene_id: string | null;
  scene_name: string | null;
  scene_state_id: string | null;
  scene_state_name: string | null;
  bound_reference_count: number;
  completeness_warnings: string[];
}

export interface ShotGenerationAssetSummary {
  keyframe_task_count: number;
  video_task_count: number;
  selected_keyframe_output_count: number;
  selected_video_output_count: number;
}

export interface ShotAssetSummary {
  id: string;
  project_id: string;
  name: string;
  characters: ShotAssetCharacterSummary[];
  scene: ShotAssetSceneSummary;
  references: SummaryReference[];
  generation: ShotGenerationAssetSummary;
  completeness_warnings: string[];
}
