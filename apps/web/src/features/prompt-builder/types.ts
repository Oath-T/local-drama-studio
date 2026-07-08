export type PromptDraftTarget = "keyframe" | "video" | "all";
export type PromptDraftStyle =
  | "cinematic_short_drama"
  | "ultra_realistic"
  | "rain_night_neon"
  | "office_drama"
  | "emotional_closeup"
  | "action_tension";
export type PromptDraftLanguage = "en";
export type PromptDraftWarningSeverity = "info" | "warning";

export interface PromptDraftOverrides {
  start_action?: string | null;
  end_action?: string | null;
  motion_direction?: string | null;
  camera_motion?: string | null;
  visual_style?: string | null;
  mood?: string | null;
}

export interface PromptDraftRequest {
  target?: PromptDraftTarget;
  style?: PromptDraftStyle;
  language?: PromptDraftLanguage;
  include_negative_prompt?: boolean;
  overrides?: PromptDraftOverrides;
}

export interface PromptDraftWarning {
  code: string;
  message: string;
  severity: PromptDraftWarningSeverity;
}

export interface PromptDraftResponse {
  source_shot_updated_at: string;
  applied_style: PromptDraftStyle;
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
