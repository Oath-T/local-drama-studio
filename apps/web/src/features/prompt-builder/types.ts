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

export interface DirectorOverrides {
  subject_position?: string | null;
  start_action?: string | null;
  end_action?: string | null;
  crowd_action?: string | null;
  crowd_emotion?: string | null;
  camera_movement?: string | null;
  composition?: string | null;
  environment_motion?: string | null;
}

export interface PromptDraftRequest {
  target?: PromptDraftTarget;
  style?: PromptDraftStyle;
  language?: PromptDraftLanguage;
  include_negative_prompt?: boolean;
  overrides?: PromptDraftOverrides;
  template_id?: string | null;
  director_overrides?: DirectorOverrides;
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
  recommended_template_id: string;
  applied_template_id: string;
  workflow_hint: string;
  director_context: DirectorContext;
  warnings: PromptDraftWarning[];
}

export interface DirectorContext {
  shot_id: string;
  template_id: string;
  subjects: DirectorSubject[];
  scene: DirectorScene;
  reaction: DirectorReaction;
  camera: DirectorCamera;
  style: DirectorStyle;
}

export interface DirectorSubject {
  shot_character_id: string | null;
  character_id: string | null;
  role: string;
  identity: string;
  look: string | null;
  position: string;
  start_action: string;
  end_action: string;
  expression_start: string | null;
  expression_end: string | null;
}

export interface DirectorScene {
  scene_id: string | null;
  state_id: string | null;
  name: string | null;
  state: string | null;
  layout: string | null;
  lighting: string | null;
  environment_motion: string | null;
}

export interface DirectorReaction {
  crowd_action: string | null;
  crowd_emotion: string | null;
}

export interface DirectorCamera {
  shot_scale: string;
  angle: string;
  height: string;
  lens: string;
  composition: string;
  movement: string;
}

export interface DirectorStyle {
  preset: PromptDraftStyle;
  aspect_ratio: string;
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
