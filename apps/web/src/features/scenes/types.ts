import type { MediaAsset } from "@/features/characters/types";

export type SceneType = "interior" | "exterior" | "mixed" | "vehicle" | "virtual" | "other";
export type TimeOfDay =
  | "dawn"
  | "morning"
  | "noon"
  | "afternoon"
  | "dusk"
  | "night"
  | "late_night"
  | "unknown";
export type Weather =
  | "clear"
  | "cloudy"
  | "overcast"
  | "light_rain"
  | "heavy_rain"
  | "storm"
  | "snow"
  | "fog"
  | "indoor"
  | "custom"
  | "unknown";
export type Lighting =
  | "natural_soft"
  | "natural_hard"
  | "warm_indoor"
  | "cool_indoor"
  | "neon"
  | "low_key"
  | "high_key"
  | "backlight"
  | "mixed"
  | "custom"
  | "unknown";
export type Season = "spring" | "summer" | "autumn" | "winter" | "not_applicable" | "unknown";
export type CrowdLevel = "empty" | "sparse" | "normal" | "crowded" | "packed" | "unknown";
export type ShotScale =
  | "extreme_wide"
  | "wide"
  | "full"
  | "medium_wide"
  | "medium"
  | "close"
  | "detail"
  | "unknown";
export type CameraPosition =
  | "eye_level"
  | "low_angle"
  | "high_angle"
  | "ground_level"
  | "overhead"
  | "aerial"
  | "doorway"
  | "corner"
  | "custom"
  | "unknown";
export type ViewDirection =
  | "front"
  | "left"
  | "right"
  | "back"
  | "diagonal_left"
  | "diagonal_right"
  | "inward"
  | "outward"
  | "custom"
  | "unknown";
export type CompositionType =
  | "centered"
  | "symmetrical"
  | "rule_of_thirds"
  | "leading_lines"
  | "frame_within_frame"
  | "deep_focus"
  | "layered"
  | "custom"
  | "unknown";
export type AnalysisStatus = "not_analyzed" | "pending" | "completed" | "failed";
export type SuggestionReviewStatus =
  | "not_reviewed"
  | "accepted"
  | "edited_and_accepted"
  | "rejected";

export interface SceneReference {
  id: string;
  state_id: string;
  media_asset_id: string;
  shot_scale: ShotScale;
  camera_position: CameraPosition;
  custom_camera_position: string | null;
  view_direction: ViewDirection;
  custom_view_direction: string | null;
  composition_type: CompositionType;
  custom_composition: string | null;
  is_empty_plate: boolean;
  is_primary: boolean;
  is_spatial_anchor: boolean;
  tags: string[];
  description: string | null;
  notes: string | null;
  analysis_status: AnalysisStatus;
  suggestion_review_status: SuggestionReviewStatus;
  analysis_suggestions: unknown | null;
  media_asset: MediaAsset;
  created_at: string;
  updated_at: string;
}

export interface SceneState {
  id: string;
  scene_id: string;
  name: string;
  description: string | null;
  time_of_day: TimeOfDay;
  weather: Weather;
  custom_weather: string | null;
  lighting: Lighting;
  custom_lighting: string | null;
  season: Season;
  environment_condition: string | null;
  crowd_level: CrowdLevel;
  prompt_state: string | null;
  is_default: boolean;
  reference_count: number;
  primary_reference: SceneReference | null;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  id: string;
  project_id: string;
  name: string;
  scene_type: SceneType;
  description: string | null;
  fixed_environment_description: string | null;
  spatial_layout_description: string | null;
  visual_style_description: string | null;
  prompt_environment: string | null;
  notes: string | null;
  default_state: SceneState | null;
  state_count: number;
  reference_count: number;
  cover_reference: SceneReference | null;
  created_at: string;
  updated_at: string;
}

export interface SceneListResponse {
  items: Scene[];
  total: number;
}

export interface SceneStateListResponse {
  items: SceneState[];
  total: number;
}

export interface SceneReferenceListResponse {
  items: SceneReference[];
  total: number;
}

export interface SceneCreateInput {
  name: string;
  scene_type: SceneType;
  description?: string | null;
  fixed_environment_description?: string | null;
  spatial_layout_description?: string | null;
  visual_style_description?: string | null;
  prompt_environment?: string | null;
  notes?: string | null;
}

export type SceneUpdateInput = Partial<SceneCreateInput>;

export interface SceneStateCreateInput {
  name: string;
  description?: string | null;
  time_of_day: TimeOfDay;
  weather: Weather;
  custom_weather?: string | null;
  lighting: Lighting;
  custom_lighting?: string | null;
  season: Season;
  environment_condition?: string | null;
  crowd_level: CrowdLevel;
  prompt_state?: string | null;
}

export type SceneStateUpdateInput = Partial<SceneStateCreateInput>;

export interface SceneReferenceUpdateInput {
  shot_scale?: ShotScale | null;
  camera_position?: CameraPosition | null;
  custom_camera_position?: string | null;
  view_direction?: ViewDirection | null;
  custom_view_direction?: string | null;
  composition_type?: CompositionType | null;
  custom_composition?: string | null;
  is_empty_plate?: boolean | null;
  is_spatial_anchor?: boolean | null;
  tags?: string[] | null;
  description?: string | null;
  notes?: string | null;
}
