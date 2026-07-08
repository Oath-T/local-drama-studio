import type {
  KeyframePromptDraftFields,
  PromptDraftResponse,
  VideoPromptDraftFields
} from "./types";

export function keyframeFieldsFromPromptDraft(
  draft: PromptDraftResponse
): KeyframePromptDraftFields {
  return {
    prompt_en: draft.first_frame_prompt_en,
    negative_prompt: draft.negative_prompt_en
  };
}

export function videoFieldsFromPromptDraft(draft: PromptDraftResponse): VideoPromptDraftFields {
  return {
    prompt: draft.motion_prompt_en,
    negative_prompt: draft.negative_prompt_en,
    camera_motion: draft.camera_motion ?? "subtle cinematic camera movement, stable framing"
  };
}

export function hasKeyframePromptConflict(values: {
  prompt_en?: string | null;
  negative_prompt?: string | null;
}): boolean {
  return hasText(values.prompt_en) || hasText(values.negative_prompt);
}

export function hasVideoPromptConflict(values: {
  prompt?: string | null;
  negative_prompt?: string | null;
  camera_motion?: string | null;
}): boolean {
  return hasText(values.prompt) || hasText(values.negative_prompt) || hasText(values.camera_motion);
}

function hasText(value: string | null | undefined): boolean {
  return Boolean(value?.trim());
}
