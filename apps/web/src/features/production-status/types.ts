export type ProductionOverallStatus = "blocked" | "in_progress" | "ready_for_video" | "completed";
export type AssetStepStatus = "complete" | "warning" | "missing";
export type DirectorPromptStatus = "not_created" | "available";
export type FrameStepStatus = "not_created" | "draft" | "ready" | "running" | "completed" | "adopted";
export type VideoStepStatus =
  | "not_created"
  | "missing_inputs"
  | "draft"
  | "ready"
  | "running"
  | "completed"
  | "adopted";
export type ProductionAction =
  | "bind_character"
  | "bind_scene"
  | "create_director_prompt"
  | "create_first_frame_task"
  | "create_end_frame_task"
  | "select_first_frame"
  | "select_end_frame"
  | "create_video_task"
  | "fill_video_inputs"
  | "review_final_output";

export interface ProductionAssetStep {
  status: AssetStepStatus;
  character_count: number;
  reference_count: number;
  has_primary_subject: boolean;
  has_scene: boolean;
  has_scene_state: boolean;
  scene_name: string | null;
  scene_state_name: string | null;
  warnings: string[];
}

export interface ProductionDirectorPromptStep {
  status: DirectorPromptStatus;
  director_template_available: boolean;
  recommended_template_id: string | null;
}

export interface ProductionFrameStep {
  status: FrameStepStatus;
  task_id: string | null;
  task_name: string | null;
  adopted_output_id: string | null;
  adopted_media_asset_id: string | null;
  content_url: string | null;
}

export interface ProductionVideoStep {
  status: VideoStepStatus;
  task_id: string | null;
  task_name: string | null;
  adopted_output_id: string | null;
  adopted_media_asset_id: string | null;
  content_url: string | null;
  has_start_frame: boolean;
  has_end_frame: boolean;
}

export interface ProductionSteps {
  assets: ProductionAssetStep;
  director_prompt: ProductionDirectorPromptStep;
  first_frame: ProductionFrameStep;
  end_frame: ProductionFrameStep;
  video: ProductionVideoStep;
  final_adoption: ProductionVideoStep;
}

export interface ContinuityCandidate {
  source_shot_id: string;
  source_shot_name: string;
  source_type: "video" | "end_frame";
  output_id: string;
  media_asset_id: string;
  content_url: string | null;
}

export interface ShotProductionStatus {
  project_id: string;
  shot_id: string;
  shot_name: string;
  order_index: number;
  overall_status: ProductionOverallStatus;
  steps: ProductionSteps;
  blockers: string[];
  next_actions: ProductionAction[];
  continuity_candidate: ContinuityCandidate | null;
  updated_at: string;
}

export interface ProjectProductionSummary {
  total_shots: number;
  blocked: number;
  in_progress: number;
  ready_for_video: number;
  completed: number;
}

export interface ProjectProductionStatus {
  project_id: string;
  summary: ProjectProductionSummary;
  items: ShotProductionStatus[];
  total: number;
}
