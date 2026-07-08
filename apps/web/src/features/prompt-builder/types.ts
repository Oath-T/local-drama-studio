export type PromptDraftTarget = "keyframe" | "video" | "all";
export type PromptDraftStyle = "cinematic_short_drama";
export type PromptDraftLanguage = "en";
export type PromptDraftWarningSeverity = "info" | "warning";

export interface PromptDraftRequest {
  target?: PromptDraftTarget;
  style?: PromptDraftStyle;
  language?: PromptDraftLanguage;
  include_negative_prompt?: boolean;
}

export interface PromptDraftWarning {
  code: string;
  message: string;
  severity: PromptDraftWarningSeverity;
}

export interface PromptDraftResponse {
  source_shot_updated_at: string;
  context_summary_zh: string;
  first_frame_prompt_en: string;
  end_frame_prompt_en: string;
  motion_prompt_en: string;
  negative_prompt_en: string;
  camera_motion: string | null;
  warnings: PromptDraftWarning[];
}

export interface KeyframePromptDraftFields {
  prompt_en: string;
  negative_prompt: string;
}

export interface VideoPromptDraftFields {
  prompt: string;
  negative_prompt: string;
  camera_motion: string;
}
