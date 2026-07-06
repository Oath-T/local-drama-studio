export type GenerationTaskType = "keyframe" | "video";
export type GenerationRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface GenerationTaskSummary {
  task_type: GenerationTaskType;
  project_id: string;
  task_id: string;
  task_name: string;
  task_status: string;
  readiness_status: string | null;
  shot_id: string;
  shot_name: string;
  workflow_id: string | null;
  latest_run_id: string | null;
  latest_run_number: number | null;
  latest_run_status: GenerationRunStatus | null;
  run_count: number;
  output_count: number;
  has_outputs: boolean;
  has_selected_output: boolean;
  created_at: string;
  updated_at: string;
}

export interface GenerationTaskSummaryListResponse {
  items: GenerationTaskSummary[];
  total: number;
}
