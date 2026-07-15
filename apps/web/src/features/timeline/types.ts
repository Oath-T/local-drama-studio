import type { MediaAsset } from "@/features/characters/types";

export type TimelineClipStatus = "ready" | "missing" | "blocked";
export type ProjectExportStatus =
  | "draft"
  | "ready"
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface TimelineFfmpegStatus {
  available: boolean;
  ffprobe_available: boolean;
  message: string | null;
}

export interface TimelineBlocker {
  code: string;
  shot_id: string | null;
  message: string;
}

export interface TimelineClip {
  shot_id: string;
  shot_order: number;
  shot_name: string;
  status: TimelineClipStatus;
  adopted_video_output_id: string | null;
  media_asset_id: string | null;
  content_url: string | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  warnings: string[];
}

export interface ProjectTimeline {
  project_id: string;
  exportable: boolean;
  total_shots: number;
  ready_clip_count: number;
  missing_clip_count: number;
  estimated_duration_seconds: number;
  project_spec: {
    aspect_ratio: string;
    default_fps: number;
  };
  ffmpeg: TimelineFfmpegStatus;
  clips: TimelineClip[];
  blockers: TimelineBlocker[];
}

export interface ProjectExportCreateRequest {
  name?: string | null;
  target_width: number;
  target_height: number;
  target_fps: number;
  video_codec?: "libx264";
}

export interface ProjectExport {
  id: string;
  project_id: string;
  name: string;
  status: ProjectExportStatus;
  progress_percent: number;
  current_stage: string;
  clip_count: number;
  duration_seconds: number | null;
  target_width: number;
  target_height: number;
  target_fps: number;
  video_codec: string;
  output_format: string;
  error_message: string | null;
  output_media_asset_id: string | null;
  output_media_asset: MediaAsset | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ProjectExportListResponse {
  items: ProjectExport[];
  total: number;
}

export interface ProjectExportStartResponse {
  id: string;
  status: ProjectExportStatus;
  progress_percent: number;
  current_stage: string;
}
