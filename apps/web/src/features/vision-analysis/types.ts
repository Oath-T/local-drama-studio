import type {
  Expression,
  PoseType,
  ShotType,
  SuggestionReviewStatus,
  ViewAngle
} from "@/features/characters/types";
import type {
  CameraPosition,
  CompositionType,
  Lighting,
  ShotScale,
  TimeOfDay,
  ViewDirection,
  Weather
} from "@/features/scenes/types";

export type VisionAnalysisTaskStatus = "pending" | "running" | "completed" | "failed";
export type VisionAnalysisTargetType = "character_reference" | "scene_reference";

export interface VisionAnalysisTask {
  id: string;
  project_id: string;
  target_type: VisionAnalysisTargetType;
  character_reference_id: string | null;
  scene_reference_id: string | null;
  provider: string;
  status: VisionAnalysisTaskStatus;
  attempt_count: number;
  error_code: string | null;
  error_message_safe: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LatestVisionAnalysisTaskResponse {
  task: VisionAnalysisTask | null;
}

export interface CharacterVisionAnalysisSuggestion {
  schema_version: number;
  shot_type: ShotType;
  view_angle: ViewAngle;
  expression: Expression;
  custom_expression: string | null;
  pose_type: PoseType;
  custom_pose: string | null;
  tags: string[];
  description: string | null;
  quality_notes: string[];
  identity_anchor_recommended: boolean;
  appearance_summary: string | null;
  costume_summary: string | null;
  hair_summary: string | null;
  confidence_notes: string | null;
}

export interface SceneVisionAnalysisSuggestion {
  schema_version: number;
  shot_scale: ShotScale;
  camera_position: CameraPosition;
  custom_camera_position: string | null;
  view_direction: ViewDirection;
  custom_view_direction: string | null;
  composition_type: CompositionType;
  custom_composition: string | null;
  tags: string[];
  description: string | null;
  quality_notes: string[];
  spatial_anchor_recommended: boolean;
  empty_plate_recommended: boolean;
  detected_time_of_day: TimeOfDay;
  detected_weather: Weather;
  detected_lighting: Lighting;
  confidence_notes: string | null;
}

export interface AnalysisConfirmInput {
  accepted_fields: string[];
  values: Record<string, unknown>;
}

export interface AnalysisConfirmResponse {
  suggestion_review_status: SuggestionReviewStatus;
}
