import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import { assetPickerCopy } from "@/features/asset-picker/copy";
import type { Character, CharacterLook, CharacterReference, MediaAsset } from "@/features/characters/types";
import { keyframeGenerationCopy } from "@/features/keyframe-generation/copy";
import type { KeyframeRun, KeyframeWorkflow, SystemCapabilities } from "@/features/keyframe-generation/types";
import { keyframeTaskCopy } from "@/features/keyframe-tasks/copy";
import type { KeyframeTask } from "@/features/keyframe-tasks/types";
import type { Scene, SceneReference, SceneState } from "@/features/scenes/types";
import { videoGenerationCopy } from "@/features/video-generation/copy";
import {
  videoTaskFormSchema,
  videoTaskFormValuesToPayload
} from "@/features/video-generation/schema";
import type { VideoRun, VideoTask, VideoWorkflow } from "@/features/video-generation/types";
import { shotCopy, shotRecommendationCopy } from "./copy";
import type { Shot, ShotRecommendationResponse } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const shotId = "22222222-2222-4222-8222-222222222222";
const characterId = "33333333-3333-4333-8333-333333333333";
const lookId = "44444444-4444-4444-8444-444444444444";
const characterReferenceId = "55555555-5555-4555-8555-555555555555";
const sceneId = "66666666-6666-4666-8666-666666666666";
const stateId = "77777777-7777-4777-8777-777777777777";
const sceneReferenceId = "88888888-8888-4888-8888-888888888888";
const secondSceneId = "12121212-1212-4121-8121-121212121212";
const secondStateId = "13131313-1313-4131-8131-131313131313";
const secondCharacterId = "14141414-1414-4141-8141-141414141414";
const secondLookId = "15151515-1515-4151-8151-151515151515";
const shotCharacterId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const shotCharacterReferenceId = "16161616-1616-4161-8161-161616161616";
const shotSceneReferenceId = "17171717-1717-4171-8171-171717171717";
const keyframeTaskId = "18181818-1818-4181-8181-181818181818";
const keyframeTaskReferenceId = "19191919-1919-4191-8191-191919191919";
const keyframeRunId = "23232323-2323-4232-8232-232323232323";
const keyframeOutputId = "24242424-2424-4242-8242-242424242424";
const videoTaskId = "26262626-2626-4262-8262-262626262626";
const videoRunId = "27272727-2727-4272-8272-272727272727";
const videoOutputId = "28282828-2828-4282-8282-282828282828";

const mediaAsset: MediaAsset = {
  id: "99999999-9999-4999-8999-999999999999",
  project_id: projectId,
  media_type: "image",
  original_filename: "reference.png",
  mime_type: "image/png",
  extension: "png",
  size_bytes: 1200,
  width: 800,
  height: 600,
  sha256: "abc123",
  thumbnail_url: "/api/media/99999999-9999-4999-8999-999999999999/thumbnail",
  content_url: "/api/media/99999999-9999-4999-8999-999999999999/content",
  created_at: "2026-06-28T10:00:00+00:00"
};

const characterReference: CharacterReference = {
  id: characterReferenceId,
  look_id: lookId,
  media_asset_id: mediaAsset.id,
  shot_type: "closeup",
  view_angle: "front",
  expression: "neutral",
  pose_type: "standing",
  custom_expression: null,
  custom_pose: null,
  tags: ["identity"],
  description: "front identity",
  notes: null,
  is_primary: true,
  is_identity_anchor: true,
  analysis_status: "not_analyzed",
  suggestion_review_status: "not_reviewed",
  analysis_suggestions: null,
  media_asset: mediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const look: CharacterLook = {
  id: lookId,
  character_id: characterId,
  name: "基础造型",
  description: null,
  costume_description: null,
  hair_description: null,
  makeup_description: null,
  condition_description: null,
  prompt_appearance: null,
  is_default: true,
  reference_count: 1,
  primary_reference: characterReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const character: Character = {
  id: characterId,
  project_id: projectId,
  name: "林知夏",
  aliases: null,
  role_type: "protagonist",
  description: null,
  appearance_description: null,
  personality_description: null,
  prompt_identity: null,
  notes: null,
  default_look: look,
  look_count: 1,
  reference_count: 1,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const sceneReference: SceneReference = {
  id: sceneReferenceId,
  state_id: stateId,
  media_asset_id: mediaAsset.id,
  shot_scale: "wide",
  camera_position: "eye_level",
  custom_camera_position: null,
  view_direction: "front",
  custom_view_direction: null,
  composition_type: "centered",
  custom_composition: null,
  is_empty_plate: false,
  is_primary: true,
  is_spatial_anchor: true,
  tags: ["lobby"],
  description: "lobby",
  notes: null,
  analysis_status: "not_analyzed",
  suggestion_review_status: "not_reviewed",
  analysis_suggestions: null,
  media_asset: mediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const state: SceneState = {
  id: stateId,
  scene_id: sceneId,
  name: "夜雨",
  description: null,
  time_of_day: "night",
  weather: "heavy_rain",
  custom_weather: null,
  lighting: "neon",
  custom_lighting: null,
  season: "unknown",
  environment_condition: null,
  crowd_level: "sparse",
  prompt_state: null,
  is_default: true,
  reference_count: 1,
  primary_reference: sceneReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const scene: Scene = {
  id: sceneId,
  project_id: projectId,
  name: "办公楼外",
  scene_type: "exterior",
  description: null,
  fixed_environment_description: null,
  spatial_layout_description: null,
  visual_style_description: null,
  prompt_environment: null,
  notes: null,
  default_state: state,
  state_count: 1,
  reference_count: 1,
  cover_reference: sceneReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const secondState: SceneState = {
  ...state,
  id: secondStateId,
  scene_id: secondSceneId,
  name: "Second State",
  primary_reference: null,
  reference_count: 0
};

const secondScene: Scene = {
  ...scene,
  id: secondSceneId,
  name: "Warehouse",
  default_state: secondState,
  cover_reference: null,
  reference_count: 0
};

const secondLook: CharacterLook = {
  ...look,
  id: secondLookId,
  character_id: characterId,
  name: "Noir Look",
  primary_reference: null,
  reference_count: 0
};

const secondCharacterLook: CharacterLook = {
  ...look,
  id: "30303030-3030-4303-8303-303030303030",
  character_id: secondCharacterId,
  name: "Second Character Look",
  primary_reference: null,
  reference_count: 0
};

const secondCharacter: Character = {
  ...character,
  id: secondCharacterId,
  name: "Second Character",
  default_look: secondCharacterLook,
  look_count: 1,
  reference_count: 0
};

const shot: Shot = {
  id: shotId,
  project_id: projectId,
  name: "镜头一",
  order_index: 1,
  story_description: null,
  visual_description: "林知夏走进雨夜。",
  dialogue: null,
  action_summary: null,
  duration_seconds: 3,
  shot_scale: "medium",
  camera_height: "eye_level",
  custom_camera_height: null,
  camera_angle: "front",
  custom_camera_angle: null,
  composition_type: "centered",
  custom_composition: null,
  camera_movement: "static",
  custom_camera_movement: null,
  focal_subject: null,
  mood_description: null,
  scene_id: sceneId,
  scene_state_id: stateId,
  scene: { id: sceneId, name: scene.name },
  scene_state: { id: stateId, name: state.name },
  notes: null,
  readiness_status: "basic_ready",
  missing_items: ["character_references", "scene_references"],
  character_count: 1,
  reference_count: 0,
  characters: [
    {
      id: shotCharacterId,
      shot_id: shotId,
      character_id: characterId,
      character_name: character.name,
      look_id: lookId,
      look_name: look.name,
      action_description: null,
      expression_description: null,
      position_description: null,
      is_primary_subject: true,
      order_index: 1,
      notes: null,
      created_at: "2026-06-28T10:00:00+00:00",
      updated_at: "2026-06-28T10:00:00+00:00"
    }
  ],
  references: [],
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const shotCharacterReferenceBinding = {
  id: shotCharacterReferenceId,
  shot_id: shotId,
  reference_type: "character" as const,
  character_reference_id: characterReferenceId,
  scene_reference_id: null,
  shot_character_id: shotCharacterId,
  purpose: "identity" as const,
  order_index: 1,
  notes: null,
  media_asset: mediaAsset,
  character_reference: characterReference,
  scene_reference: null,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const shotSceneReferenceBinding = {
  id: shotSceneReferenceId,
  shot_id: shotId,
  reference_type: "scene" as const,
  character_reference_id: null,
  scene_reference_id: sceneReferenceId,
  shot_character_id: null,
  purpose: "environment" as const,
  order_index: 2,
  notes: null,
  media_asset: mediaAsset,
  character_reference: null,
  scene_reference: sceneReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const shotWithReferences: Shot = {
  ...shot,
  references: [shotCharacterReferenceBinding, shotSceneReferenceBinding],
  reference_count: 2,
  readiness_status: "asset_ready",
  missing_items: []
};

const keyframeTask: KeyframeTask = {
  id: keyframeTaskId,
  project_id: projectId,
  shot_id: shotId,
  name: "关键帧任务 1",
  status: "draft",
  shot_snapshot: {
    schema_version: 1,
    shot_id: shotId,
    order_index: 1,
    title: shot.name,
    story_description: shot.story_description,
    visual_description: shot.visual_description,
    action_summary: shot.action_summary,
    dialogue: shot.dialogue,
    mood_description: shot.mood_description,
    duration_seconds: shot.duration_seconds,
    shot_scale: shot.shot_scale,
    camera_angle: shot.camera_angle,
    custom_camera_angle: shot.custom_camera_angle,
    camera_height: shot.camera_height,
    custom_camera_height: shot.custom_camera_height,
    lens: null,
    composition_type: shot.composition_type,
    custom_composition: shot.custom_composition,
    camera_movement: shot.camera_movement,
    custom_camera_movement: shot.custom_camera_movement,
    scene_id: sceneId,
    scene_name: scene.name,
    scene_state_id: stateId,
    scene_state_name: state.name,
    characters: [
      {
        shot_character_id: shotCharacterId,
        character_id: characterId,
        character_name: character.name,
        look_id: lookId,
        look_name: look.name,
        action_description: null,
        expression_description: null,
        position_description: null,
        is_primary_subject: true,
        order_index: 1
      }
    ]
  },
  source_shot_updated_at: "2026-06-28T10:00:00+00:00",
  prompt_zh: "中文提示词",
  prompt_en: null,
  negative_prompt: "低质量",
  aspect_ratio: "9:16",
  width: 768,
  height: 1360,
  seed: null,
  steps: 30,
  guidance_scale: 7,
  sampler_name: null,
  scheduler_name: null,
  model_provider: null,
  model_name: null,
  model_version: null,
  output_count: 1,
  readiness: {
    readiness_status: "ready",
    blocking_issues: [],
    warnings: ["no_english_prompt", "no_model_selected", "no_seed"]
  },
  shot_changed_since_snapshot: false,
  references: [
    {
      id: keyframeTaskReferenceId,
      task_id: keyframeTaskId,
      reference_type: "character",
      shot_reference_id: shotCharacterReferenceId,
      character_reference_id: characterReferenceId,
      scene_reference_id: null,
      media_asset_id: mediaAsset.id,
      purpose: "identity",
      order_index: 1,
      source_shot_character_id: shotCharacterId,
      source_character_id: characterId,
      source_look_id: lookId,
      source_scene_id: null,
      source_scene_state_id: null,
      source_reference_deleted: false,
      media_asset: mediaAsset,
      created_at: "2026-06-28T10:00:00+00:00"
    }
  ],
  reference_count: 1,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const keyframeWorkflow: KeyframeWorkflow = {
  workflow_id: "keyframe_basic_v1",
  display_name: "基础文生图关键帧",
  version: "1.0.0",
  available: true,
  missing_requirements: [],
  uses_reference_inputs: false
};

const systemCapabilities: SystemCapabilities = {
  vision_analysis: { available: false, provider: "openai" },
  keyframe_generation: { available: true, provider: "comfyui", status: "online" },
  video_generation: { available: true, provider: "comfyui", status: "online" }
};

const keyframeRun: KeyframeRun = {
  id: keyframeRunId,
  project_id: projectId,
  keyframe_task_id: keyframeTaskId,
  run_number: 1,
  provider: "comfyui",
  workflow_id: "keyframe_basic_v1",
  workflow_version: "1.0.0",
  status: "completed",
  provider_job_id: "prompt-1",
  submitted_payload_snapshot: {
    schema_version: 1,
    task_id: keyframeTaskId,
    task_updated_at: keyframeTask.updated_at,
    workflow_id: "keyframe_basic_v1",
    workflow_version: "1.0.0",
    prompt_zh: keyframeTask.prompt_zh,
    prompt_en: null,
    effective_prompt_language: "zh",
    effective_positive_prompt: keyframeTask.prompt_zh ?? "",
    negative_prompt: keyframeTask.negative_prompt,
    width: keyframeTask.width,
    height: keyframeTask.height,
    seed: 123,
    steps: keyframeTask.steps,
    guidance_scale: keyframeTask.guidance_scale,
    sampler_name: "euler",
    scheduler_name: "normal",
    output_count: 1,
    task_reference_ids: [keyframeTaskReferenceId],
    media_asset_ids: [mediaAsset.id],
    reference_inputs_used: false
  },
  error_code: null,
  error_message_safe: null,
  queued_at: "2026-06-28T10:00:00+00:00",
  started_at: "2026-06-28T10:00:01+00:00",
  completed_at: "2026-06-28T10:00:05+00:00",
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:05+00:00",
  outputs: [
    {
      id: keyframeOutputId,
      project_id: projectId,
      run_id: keyframeRunId,
      media_asset_id: mediaAsset.id,
      output_index: 1,
      width: 768,
      height: 1360,
      seed: 123,
      is_selected: false,
      media_asset: mediaAsset,
      created_at: "2026-06-28T10:00:05+00:00"
    }
  ]
};

const videoWorkflow: VideoWorkflow = {
  workflow_id: "video_i2v_14b_v1",
  display_name: "Video I2V 14B Basic",
  version: "0.1.0",
  mode: "single_image_to_video",
  required_input_roles: ["start_frame"],
  available: false,
  missing_requirements: ["workflow_file_missing"],
  reference_inputs_used: true
};

const videoTask: VideoTask = {
  id: videoTaskId,
  project_id: projectId,
  shot_id: shotId,
  name: "视频生成任务",
  status: "draft",
  input_media_asset_id: mediaAsset.id,
  source_keyframe_output_id: null,
  source_keyframe_task_id: null,
  prompt: "雨夜街道逐渐推进",
  negative_prompt: null,
  duration_seconds: 5,
  fps: 16,
  width: 768,
  height: 1360,
  seed: null,
  motion_strength: null,
  camera_motion: null,
  workflow_id: "video_i2v_14b_v1",
  input_media_asset: mediaAsset,
  inputs: [
    {
      id: "video-input-start",
      role: "start_frame",
      media_asset_id: mediaAsset.id,
      source_keyframe_output_id: null,
      source_keyframe_task_id: null,
      sort_order: 1,
      media_asset: mediaAsset,
      created_at: "2026-06-28T10:00:00+00:00",
      updated_at: "2026-06-28T10:00:00+00:00"
    }
  ],
  readiness: {
    readiness_status: "incomplete",
    blocking_issues: ["workflow_unavailable"],
    warnings: ["no_negative_prompt", "no_camera_motion", "no_seed"]
  },
  latest_run_status: null,
  selected_output: null,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

function applyVideoTaskPayload(task: VideoTask, payload: Record<string, unknown>): VideoTask {
  const next = { ...task, ...payload, status: "draft" as const };
  if (Array.isArray(payload.inputs)) {
    const inputs = payload.inputs as Array<{
      role: "start_frame" | "end_frame";
      media_asset_id?: string | null;
      source_keyframe_output_id?: string | null;
      source_keyframe_task_id?: string | null;
    }>;
    next.inputs = inputs.map((input, index) => ({
      id: `video-input-${input.role}`,
      role: input.role,
      media_asset_id:
        input.media_asset_id ?? (input.source_keyframe_output_id ? mediaAsset.id : null),
      source_keyframe_output_id: input.source_keyframe_output_id ?? null,
      source_keyframe_task_id: input.source_keyframe_task_id ?? null,
      sort_order: index + 1,
      media_asset:
        input.media_asset_id || input.source_keyframe_output_id ? mediaAsset : null,
      created_at: "2026-06-28T10:00:00+00:00",
      updated_at: "2026-06-28T10:00:00+00:00"
    }));
    const startInput = next.inputs.find((input) => input.role === "start_frame");
    next.input_media_asset_id = startInput?.media_asset_id ?? null;
    next.input_media_asset = startInput?.media_asset ?? null;
    next.source_keyframe_output_id = startInput?.source_keyframe_output_id ?? null;
    next.source_keyframe_task_id = startInput?.source_keyframe_task_id ?? null;
  }
  return next;
}

const videoRun: VideoRun = {
  id: videoRunId,
  project_id: projectId,
  video_task_id: videoTaskId,
  run_number: 1,
  provider: "comfyui",
  workflow_id: "video_i2v_14b_v1",
  workflow_version: "0.1.0",
  status: "completed",
  provider_job_id: "video-prompt-1",
  submitted_payload_snapshot: {
    schema_version: 1,
    video_task_id: videoTaskId,
    shot_id: shotId,
    workflow_id: "video_i2v_14b_v1",
    workflow_version: "0.1.0",
    input_media_asset_id: mediaAsset.id,
    prompt: "雨夜街道逐渐推进",
    negative_prompt: null,
    duration_seconds: 5,
    fps: 16,
    width: 768,
    height: 1360,
    seed: 123,
    motion_strength: null,
    camera_motion: null,
    reference_inputs_used: true
  },
  error_code: null,
  error_message_safe: null,
  queued_at: "2026-06-28T10:00:00+00:00",
  started_at: "2026-06-28T10:00:01+00:00",
  completed_at: "2026-06-28T10:00:05+00:00",
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:05+00:00",
  outputs: [
    {
      id: videoOutputId,
      project_id: projectId,
      run_id: videoRunId,
      media_asset_id: mediaAsset.id,
      output_index: 1,
      width: 768,
      height: 1360,
      duration_seconds: 5,
      fps: 16,
      seed: 123,
      is_selected: false,
      media_asset: { ...mediaAsset, media_type: "video", thumbnail_url: null, mime_type: "video/mp4", extension: "mp4" },
      created_at: "2026-06-28T10:00:05+00:00"
    }
  ]
};

const recommendations: ShotRecommendationResponse = {
  shot_id: shotId,
  generated_from_updated_at: shot.updated_at,
  character_recommendations: [
    {
      shot_character_id: shot.characters[0].id,
      character_id: characterId,
      character_name: character.name,
      look_id: lookId,
      look_name: look.name,
      items: [
        {
          reference_id: characterReferenceId,
          media_asset_id: mediaAsset.id,
          thumbnail_url: mediaAsset.thumbnail_url ?? mediaAsset.content_url,
          content_url: mediaAsset.content_url,
          source_look_id: lookId,
          source_look_name: look.name,
          shot_type: "closeup",
          view_angle: "front",
          expression: "neutral",
          pose_type: "standing",
          is_primary: true,
          is_identity_anchor: true,
          score: 90,
          suggested_purpose: "identity",
          reasons: ["look_exact_match", "identity_anchor"],
          bound_purposes: [],
          is_already_bound_for_suggested_purpose: false
        }
      ]
    }
  ],
  scene_recommendations: {
    status_code: "ready",
    items: [
      {
        reference_id: sceneReferenceId,
        media_asset_id: mediaAsset.id,
        thumbnail_url: mediaAsset.thumbnail_url ?? mediaAsset.content_url,
        content_url: mediaAsset.content_url,
        source_state_id: stateId,
        source_state_name: state.name,
        shot_scale: "wide",
        camera_position: "eye_level",
        view_direction: "front",
        composition_type: "centered",
        is_primary: true,
        is_spatial_anchor: true,
        is_empty_plate: false,
        score: 95,
        suggested_purpose: "spatial",
        reasons: ["spatial_anchor", "composition_exact"],
        bound_purposes: [],
        is_already_bound_for_suggested_purpose: false
      }
    ]
  }
};

function renderRoute(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function mockShotApi(
  options: {
    shots?: Shot[];
    scenes?: Scene[];
    characters?: Character[];
    statesByScene?: Record<string, SceneState[]>;
    failReference?: boolean;
    failRecommendations?: boolean;
    recommendations?: ShotRecommendationResponse;
    failScenes?: boolean;
    failCharacters?: boolean;
    failShotUpdate?: boolean;
    keyframeTasks?: KeyframeTask[];
    failKeyframeTasks?: boolean;
    failKeyframeUpdate?: boolean;
    capabilities?: SystemCapabilities;
    failCapabilities?: boolean;
    workflows?: KeyframeWorkflow[];
    failWorkflows?: boolean;
    keyframeRuns?: KeyframeRun[];
    failKeyframeRuns?: boolean;
    failStartRun?: boolean;
    videoWorkflows?: VideoWorkflow[];
    videoTasks?: VideoTask[];
    failVideoTasks?: boolean;
    videoRuns?: VideoRun[];
    failVideoRuns?: boolean;
  } = {}
) {
  const requests: Array<{ url: string; method: string; body?: string }> = [];
  let shots = options.shots ?? [shot];
  let keyframeTasks = options.keyframeTasks ?? [];
  let keyframeRuns = options.keyframeRuns ?? [];
  let videoTasks = options.videoTasks ?? [];
  let videoRuns = options.videoRuns ?? [];
  const scenes = options.scenes ?? [scene];
  const characters = options.characters ?? [character];
  const statesByScene = options.statesByScene ?? { [sceneId]: [state] };
  const currentShot = () => shots.find((item) => item.id === shotId) ?? shot;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? init.body : undefined;
    requests.push({ url, method, body });

    if (url === "/api/health") return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    if (url === "/api/system/capabilities") {
      if (options.failCapabilities) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse(options.capabilities ?? systemCapabilities);
    }
    if (url === `/api/projects/${projectId}`) {
      return jsonResponse({
        id: projectId,
        name: "测试项目",
        description: null,
        aspect_ratio: "9:16",
        default_style: null,
        default_language: "zh-CN",
        default_fps: 24,
        cover_image_path: null,
        created_at: "2026-06-28T10:00:00+00:00",
        updated_at: "2026-06-28T10:00:00+00:00"
      });
    }
    if (url === `/api/projects/${projectId}/shots` && method === "GET") {
      return jsonResponse({ items: shots, total: shots.length });
    }
    if (url === `/api/projects/${projectId}/shots` && method === "POST") {
      const created = { ...shot, id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "镜头 1" };
      shots = [created];
      return jsonResponse(created, 201);
    }
    if (url === `/api/projects/${projectId}/keyframe-workflows` && method === "GET") {
      if (options.failWorkflows) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      const workflows = options.workflows ?? [keyframeWorkflow];
      return jsonResponse({ items: workflows, total: workflows.length });
    }
    if (url === `/api/projects/${projectId}/video-workflows` && method === "GET") {
      const workflows = options.videoWorkflows ?? [videoWorkflow];
      return jsonResponse({ items: workflows, total: workflows.length });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}/video-tasks` && method === "GET") {
      if (options.failVideoTasks) {
        return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      }
      return jsonResponse({ items: videoTasks, total: videoTasks.length });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}/video-tasks` && method === "POST") {
      const payload = body ? JSON.parse(body) : {};
      const created = applyVideoTaskPayload({ ...videoTask, id: videoTaskId }, payload);
      videoTasks = [created, ...videoTasks];
      return jsonResponse(created, 201);
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}` && method === "PATCH") {
      const patch = body ? JSON.parse(body) : {};
      const updated = applyVideoTaskPayload(videoTasks[0] ?? videoTask, patch);
      videoTasks = videoTasks.map((item) => (item.id === videoTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/video-inputs/images` && method === "POST") {
      return jsonResponse({ media_asset: mediaAsset }, 201);
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}` && method === "DELETE") {
      videoTasks = videoTasks.filter((item) => item.id !== videoTaskId);
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}/mark-ready` && method === "POST") {
      const updated = {
        ...(videoTasks[0] ?? videoTask),
        status: "ready" as const,
        readiness: { readiness_status: "ready" as const, blocking_issues: [], warnings: [] }
      };
      videoTasks = videoTasks.map((item) => (item.id === videoTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}/mark-draft` && method === "POST") {
      const updated = { ...(videoTasks[0] ?? videoTask), status: "draft" as const };
      videoTasks = videoTasks.map((item) => (item.id === videoTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}/runs` && method === "GET") {
      if (options.failVideoRuns) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: videoRuns, total: videoRuns.length });
    }
    if (url === `/api/projects/${projectId}/video-tasks/${videoTaskId}/runs` && method === "POST") {
      const queuedRun = { ...videoRun, status: "queued" as const };
      videoRuns = videoRuns.some((run) => run.id === videoRun.id)
        ? videoRuns.map((run) => (run.id === videoRun.id ? queuedRun : run))
        : [queuedRun, ...videoRuns];
      return jsonResponse({ run_id: videoRun.id, status: "queued" }, 202);
    }
    if (url === `/api/projects/${projectId}/video-outputs/${videoOutputId}/select` && method === "POST") {
      videoRuns = videoRuns.map((run) => ({
        ...run,
        outputs: run.outputs.map((output) => ({ ...output, is_selected: output.id === videoOutputId }))
      }));
      return jsonResponse({ ...videoRun.outputs[0], is_selected: true });
    }
    if (url === `/api/projects/${projectId}/video-outputs/${videoOutputId}/select` && method === "DELETE") {
      videoRuns = videoRuns.map((run) => ({
        ...run,
        outputs: run.outputs.map((output) => ({ ...output, is_selected: false }))
      }));
      return jsonResponse({ ...videoRun.outputs[0], is_selected: false });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}/keyframe-tasks` && method === "GET") {
      if (options.failKeyframeTasks) {
        return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      }
      return jsonResponse({ items: keyframeTasks, total: keyframeTasks.length });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}/keyframe-tasks` && method === "POST") {
      const created = { ...keyframeTask, id: "20202020-2020-4202-8202-202020202020" };
      keyframeTasks = [created, ...keyframeTasks];
      return jsonResponse(created, 201);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}` && method === "GET") {
      return jsonResponse(keyframeTasks.find((item) => item.id === keyframeTaskId) ?? keyframeTask);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}` && method === "PATCH") {
      if (options.failKeyframeUpdate) {
        return jsonResponse({ error: { code: "KEYFRAME_TASK_NOT_READY", message: "not ready" } }, 400);
      }
      const patch = body ? JSON.parse(body) : {};
      const updated = { ...(keyframeTasks[0] ?? keyframeTask), ...patch, status: "draft" } as KeyframeTask;
      keyframeTasks = keyframeTasks.map((item) => (item.id === keyframeTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}` && method === "DELETE") {
      keyframeTasks = keyframeTasks.filter((item) => item.id !== keyframeTaskId);
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/duplicate` && method === "POST") {
      const duplicate = {
        ...keyframeTask,
        id: "21212121-2121-4212-8212-212121212121",
        name: "关键帧任务 1 - 副本"
      };
      keyframeTasks = [duplicate, ...keyframeTasks];
      return jsonResponse(duplicate);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/mark-ready` && method === "POST") {
      const updated = { ...keyframeTask, status: "ready" as const };
      keyframeTasks = keyframeTasks.map((item) => (item.id === keyframeTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/mark-draft` && method === "POST") {
      const updated = { ...keyframeTask, status: "draft" as const };
      keyframeTasks = keyframeTasks.map((item) => (item.id === keyframeTaskId ? updated : item));
      return jsonResponse(updated);
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/runs` && method === "GET") {
      if (options.failKeyframeRuns) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: keyframeRuns, total: keyframeRuns.length });
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/runs` && method === "POST") {
      if (options.failStartRun) {
        return jsonResponse(
          { error: { code: "workflow_output_count_unsupported", message: "unsupported" } },
          422
        );
      }
      keyframeRuns = [{ ...keyframeRun, status: "queued" }, ...keyframeRuns];
      return jsonResponse({ run_id: keyframeRun.id, status: "queued" }, 202);
    }
    if (url === `/api/projects/${projectId}/keyframe-runs/${keyframeRunId}` && method === "GET") {
      return jsonResponse(keyframeRuns.find((run) => run.id === keyframeRunId) ?? keyframeRun);
    }
    if (url === `/api/projects/${projectId}/keyframe-runs/${keyframeRunId}/retry` && method === "POST") {
      const retryRun = {
        ...keyframeRun,
        id: "25252525-2525-4252-8252-252525252525",
        run_number: 2,
        status: "queued" as const
      };
      keyframeRuns = [retryRun, ...keyframeRuns];
      return jsonResponse({ run_id: retryRun.id, status: "queued" }, 202);
    }
    if (url === `/api/projects/${projectId}/keyframe-outputs/${keyframeOutputId}/select` && method === "POST") {
      keyframeRuns = keyframeRuns.map((run) => ({
        ...run,
        outputs: run.outputs.map((output) => ({ ...output, is_selected: output.id === keyframeOutputId }))
      }));
      return jsonResponse({ ...keyframeRun.outputs[0], is_selected: true });
    }
    if (url === `/api/projects/${projectId}/keyframe-outputs/${keyframeOutputId}/select` && method === "DELETE") {
      keyframeRuns = keyframeRuns.map((run) => ({
        ...run,
        outputs: run.outputs.map((output) => ({ ...output, is_selected: false }))
      }));
      return jsonResponse({ ...keyframeRun.outputs[0], is_selected: false });
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/references` && method === "GET") {
      return jsonResponse({ items: keyframeTask.references, total: keyframeTask.references.length });
    }
    if (url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/references` && method === "POST") {
      const patch = body ? JSON.parse(body) : {};
      const addedReference = {
        ...keyframeTask.references[0],
        id: "22222222-2222-4222-8222-222222222221",
        shot_reference_id: patch.shot_reference_id,
        purpose: patch.purpose,
        order_index: keyframeTask.references.length + 1
      };
      const updated = {
        ...keyframeTask,
        references: [...keyframeTask.references, addedReference],
        reference_count: keyframeTask.references.length + 1
      };
      keyframeTasks = keyframeTasks.map((item) => (item.id === keyframeTaskId ? updated : item));
      return jsonResponse(updated, 201);
    }
    if (
      url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/references/${keyframeTaskReferenceId}` &&
      method === "PATCH"
    ) {
      const patch = body ? JSON.parse(body) : {};
      const updated = {
        ...keyframeTask,
        references: keyframeTask.references.map((reference) =>
          reference.id === keyframeTaskReferenceId ? { ...reference, ...patch } : reference
        )
      };
      return jsonResponse(updated);
    }
    if (
      url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}/references/${keyframeTaskReferenceId}` &&
      method === "DELETE"
    ) {
      return emptyResponse();
    }
    if (url.startsWith(`/api/projects/${projectId}/assets/picker-options`)) {
      const parsed = new URL(url, "http://test.local");
      const assetType = parsed.searchParams.get("asset_type");
      if (assetType === "character") {
        const items = characters.map((item) => ({
          id: item.id,
          type: "character",
          name: item.name,
          description: item.description,
          thumbnail_url: item.default_look?.primary_reference?.media_asset.thumbnail_url ?? null,
          content_url: item.default_look?.primary_reference?.media_asset.content_url ?? null,
          badges: item.id === characterId ? ["已绑定"] : ["身份基准图"],
          source: { kind: "character", label: "人物库" },
          is_selected: currentShot().characters.some((shotCharacter) => shotCharacter.character_id === item.id),
          is_adopted: false,
          metadata: {
            default_look_id: item.default_look?.id ?? null,
            reference_count: item.reference_count
          }
        }));
        return jsonResponse({ items, total: items.length });
      }
      if (assetType === "scene") {
        const items = scenes.map((item) => ({
          id: item.id,
          type: "scene",
          name: item.name,
          description: item.description,
          thumbnail_url: item.cover_reference?.media_asset.thumbnail_url ?? null,
          content_url: item.cover_reference?.media_asset.content_url ?? null,
          badges: item.id === currentShot().scene_id ? ["当前使用"] : ["空间结构参考图"],
          source: { kind: "scene", label: "场景库" },
          is_selected: item.id === currentShot().scene_id,
          is_adopted: false,
          metadata: {
            default_state_id: item.default_state?.id ?? null,
            reference_count: item.reference_count
          }
        }));
        return jsonResponse({ items, total: items.length });
      }
      if (assetType === "character_look") {
        const characterIdParam = parsed.searchParams.get("character_id");
        const shotCharacterIdParam = parsed.searchParams.get("shot_character_id");
        const looks = characterIdParam === characterId ? [look, secondLook] : [secondCharacterLook];
        const items = looks.map((item) => ({
          id: item.id,
          type: "character_look",
          name: item.name,
          description: item.description,
          thumbnail_url: item.primary_reference?.media_asset.thumbnail_url ?? null,
          content_url: item.primary_reference?.media_asset.content_url ?? null,
          badges: [
            ...(item.is_default ? ["默认造型"] : []),
            ...(item.id === lookId && shotCharacterIdParam === shotCharacterId ? ["当前使用"] : [])
          ],
          source: { kind: "character_look", label: "角色造型" },
          is_selected: item.id === lookId && shotCharacterIdParam === shotCharacterId,
          is_adopted: false,
          metadata: {
            character_id: item.character_id,
            reference_count: item.reference_count
          }
        }));
        return jsonResponse({ items, total: items.length });
      }
      if (assetType === "scene_state") {
        const sceneIdParam = parsed.searchParams.get("scene_id") ?? sceneId;
        const items = (statesByScene[sceneIdParam] ?? []).map((item) => ({
          id: item.id,
          type: "scene_state",
          name: item.name,
          description: item.description,
          thumbnail_url: item.primary_reference?.media_asset.thumbnail_url ?? null,
          content_url: item.primary_reference?.media_asset.content_url ?? null,
          badges: [
            ...(item.is_default ? ["默认状态"] : []),
            ...(item.id === currentShot().scene_state_id ? ["当前使用"] : [])
          ],
          source: { kind: "scene_state", label: "场景状态" },
          is_selected: item.id === currentShot().scene_state_id,
          is_adopted: false,
          metadata: {
            scene_id: item.scene_id,
            reference_count: item.reference_count
          }
        }));
        return jsonResponse({ items, total: items.length });
      }
      if (assetType === "reference_image") {
        const taskIdParam = parsed.searchParams.get("task_id");
        const taskReferenceIds = new Set(
          taskIdParam
            ? (keyframeTasks.find((item) => item.id === taskIdParam)?.references ?? []).map(
                (reference) => reference.shot_reference_id
              )
            : []
        );
        const items = [
          ...currentShot().references.map((reference) => {
            const referenceMedia = reference.media_asset ?? mediaAsset;
            return {
              id: reference.id,
              type: "reference_image",
              name: referenceMedia.original_filename,
              description:
                reference.character_reference?.description ??
                reference.scene_reference?.description ??
                "镜头参考图",
              thumbnail_url: referenceMedia.thumbnail_url,
              content_url: referenceMedia.content_url,
              badges: [
                "镜头参考图",
                ...(taskReferenceIds.has(reference.id) ? ["已加入任务"] : [])
              ],
              source: { kind: "shot_reference", label: "镜头参考图" },
              is_selected: taskIdParam ? taskReferenceIds.has(reference.id) : true,
              is_adopted: false,
              metadata: {
                reference_type: reference.reference_type,
                shot_reference_id: reference.id,
                character_reference_id: reference.character_reference_id,
                scene_reference_id: reference.scene_reference_id,
                shot_character_id: reference.shot_character_id,
                purpose: reference.purpose,
                suggested_purpose: reference.purpose,
                is_bound_to_shot: true,
                is_added_to_task: taskReferenceIds.has(reference.id)
              }
            };
          }),
          {
            id: characterReferenceId,
            type: "reference_image",
            name: mediaAsset.original_filename,
            description: characterReference.description,
            thumbnail_url: mediaAsset.thumbnail_url,
            content_url: mediaAsset.content_url,
            badges: ["身份基准图", "主图"],
            source: { kind: "character_reference", label: "人物参考图" },
            is_selected: false,
            is_adopted: false,
            metadata: {
              reference_type: "character",
              shot_reference_id: null,
              character_reference_id: characterReferenceId,
              scene_reference_id: null,
              shot_character_id: shotCharacterId,
              purpose: "identity",
              suggested_purpose: "identity",
              is_bound_to_shot: false,
              is_added_to_task: false
            }
          },
          {
            id: sceneReferenceId,
            type: "reference_image",
            name: mediaAsset.original_filename,
            description: sceneReference.description,
            thumbnail_url: mediaAsset.thumbnail_url,
            content_url: mediaAsset.content_url,
            badges: ["空间结构参考图", "主图"],
            source: { kind: "scene_reference", label: "场景参考图" },
            is_selected: false,
            is_adopted: false,
            metadata: {
              reference_type: "scene",
              shot_reference_id: null,
              character_reference_id: null,
              scene_reference_id: sceneReferenceId,
              shot_character_id: null,
              purpose: "environment",
              suggested_purpose: "environment",
              is_bound_to_shot: false,
              is_added_to_task: false
            }
          }
        ];
        return jsonResponse({ items, total: items.length });
      }
      if (assetType === "frame_image") {
        const items = [
          {
            id: mediaAsset.id,
            type: "frame_image",
            name: mediaAsset.original_filename,
            description: "关键帧输出",
            thumbnail_url: mediaAsset.thumbnail_url,
            content_url: mediaAsset.content_url,
            badges: ["关键帧输出"],
            source: { kind: "keyframe_output", label: "关键帧输出" },
            is_selected: false,
            is_adopted: false,
            metadata: {
              media_asset_id: mediaAsset.id,
              keyframe_output_id: keyframeOutputId,
              keyframe_task_id: keyframeTaskId
            }
          }
        ];
        return jsonResponse({ items, total: items.length });
      }
    }
    if (url.includes("/recommendations?limit=5")) {
      if (options.failRecommendations) {
        return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      }
      return jsonResponse(options.recommendations ?? recommendations);
    }
    if (url.startsWith(`/api/projects/${projectId}/shots/`) && method === "GET" && !url.includes("/characters") && !url.includes("/references") && !url.includes("/recommendations") && !url.includes("/keyframe-tasks")) {
      const id = url.split("/shots/")[1];
      return jsonResponse(shots.find((item) => item.id === id) ?? shot);
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}` && method === "PATCH") {
      if (options.failShotUpdate) {
        return jsonResponse(
          { error: { code: "SHOT_DURATION_SECONDS_POSITIVE", message: "invalid duration" } },
          422
        );
      }
      return jsonResponse({ ...shot, ...(body ? JSON.parse(body) : {}) });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}` && method === "DELETE") return emptyResponse();
    if (url === `/api/projects/${projectId}/shots/${shotId}/move` && method === "POST") return jsonResponse(shot);
    if (url === `/api/projects/${projectId}/shots/${shotId}/duplicate` && method === "POST") return jsonResponse({ ...shot, id: "copy", name: "镜头一 - 副本" });
    if (url === `/api/projects/${projectId}/shots/${shotId}/characters` && method === "GET") return jsonResponse({ items: currentShot().characters, total: currentShot().characters.length });
    if (url === `/api/projects/${projectId}/shots/${shotId}/characters` && method === "POST") return jsonResponse(currentShot().characters[0], 201);
    if (url.includes("/characters/") && method === "PATCH") return jsonResponse(currentShot().characters[0]);
    if (url.includes("/characters/") && method === "DELETE") return emptyResponse();
    if (url === `/api/projects/${projectId}/shots/${shotId}/references` && method === "GET") return jsonResponse({ items: currentShot().references, total: currentShot().references.length });
    if (url === `/api/projects/${projectId}/shots/${shotId}/references` && method === "POST") {
      if (options.failReference) return jsonResponse({ error: { code: "SHOT_REFERENCE_ALREADY_BOUND", message: "duplicate" } }, 409);
      return jsonResponse({ ...currentShot().references[0], id: "new-ref" }, 201);
    }
    if (url.includes("/references/") && method === "DELETE") return emptyResponse();
    if (url.includes("/references/") && method === "PATCH") return jsonResponse(currentShot().references[0]);
    if (url === `/api/projects/${projectId}/characters`) {
      if (options.failCharacters) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: characters, total: characters.length });
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks`) return jsonResponse({ items: [look, secondLook], total: 2 });
    if (url === `/api/projects/${projectId}/characters/${secondCharacterId}/looks`) return jsonResponse({ items: [secondCharacterLook], total: 1 });
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references`) return jsonResponse({ items: [characterReference], total: 1 });
    if (url === `/api/projects/${projectId}/scenes`) {
      if (options.failScenes) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: scenes, total: scenes.length });
    }
    if (url.startsWith(`/api/projects/${projectId}/scenes/`) && url.endsWith("/states")) {
      const id = url.split("/scenes/")[1].split("/states")[0];
      const items = statesByScene[id] ?? [];
      return jsonResponse({ items, total: items.length });
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references`) return jsonResponse({ items: [sceneReference], total: 1 });
    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });
  return { requests };
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

function emptyResponse() {
  return Promise.resolve(new Response(null, { status: 204 }));
}

describe("shot workbench routes", () => {
  it("renders a global project guide without guessing project", async () => {
    mockShotApi();
    renderRoute("/shots");

    expect(await screen.findByText("请先选择一个项目")).toBeInTheDocument();
  });

  it("renders empty state and creates the first shot", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ shots: [] });
    renderRoute(`/projects/${projectId}/shots`);

    expect(await screen.findByText("当前项目还没有镜头")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "新建镜头" })[0]);

    expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/shots"))).toBe(true);
  });

  it("renders the three-panel workbench and saves shot edits", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByRole("heading", { name: "镜头工作台" })).toBeInTheDocument();
    expect(await screen.findByText("镜头列表")).toBeInTheDocument();
    expect(await screen.findByText("镜头信息")).toBeInTheDocument();
    expect(await screen.findByText(shotRecommendationCopy.tabs.smart)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("镜头名称"));
    await user.type(screen.getByLabelText("镜头名称"), "雨夜入场");
    await user.click(screen.getByRole("button", { name: "保存镜头" }));

    expect(requests.some((request) => request.method === "PATCH" && request.body?.includes("雨夜入场"))).toBe(true);
  });

  it("adds a shot character through the asset picker", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ characters: [character, secondCharacter] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseCharacter }));
    await user.click(await screen.findByRole("button", { name: /Second Character/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/characters`) &&
            request.body?.includes(secondCharacterId)
        )
      ).toBe(true);
    });
  });

  it("updates the shot scene through the asset picker without choosing a state", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ scenes: [scene, secondScene] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseScene }));
    await user.click(await screen.findByRole("button", { name: /Warehouse/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      const request = requests.find(
        (item) => item.method === "PATCH" && item.url === `/api/projects/${projectId}/shots/${shotId}`
      );
      expect(request).toBeTruthy();
      const payload = JSON.parse(request?.body ?? "{}");
      expect(payload.scene_id).toBe(secondSceneId);
      expect(payload.scene_state_id).toBeNull();
    });
  });

  it("updates a shot character look through the asset picker", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ characters: [character] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseCharacterLook }));
    await user.click(await screen.findByRole("button", { name: /Noir Look/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url.endsWith(`/shots/${shotId}/characters/${shotCharacterId}`) &&
            request.body?.includes(secondLookId)
        )
      ).toBe(true);
    });
  });

  it("updates the shot scene state through the asset picker", async () => {
    const user = userEvent.setup();
    const alternateState = { ...secondState, scene_id: sceneId, name: "清晨大厅" };
    const { requests } = mockShotApi({
      statesByScene: { [sceneId]: [state, alternateState] }
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const sceneSelect = await screen.findByRole("combobox", { name: shotCopy.fields.scene });
    await user.click(sceneSelect);
    await user.click(await screen.findByRole("option", { name: scene.name }));
    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseSceneState }));
    const stateOption = (await screen.findAllByText("清晨大厅"))
      .map((item) => item.closest("button"))
      .find(Boolean);
    expect(stateOption).toBeDefined();
    await user.click(stateOption!);
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url === `/api/projects/${projectId}/shots/${shotId}` &&
            request.body?.includes(secondStateId)
        )
      ).toBe(true);
    });
  });

  it("adds a shot reference from shot-context asset picker options", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseReferenceImage }));
    await user.click((await screen.findAllByRole("button", { name: /reference\.png/ }))[0]);
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/references`) &&
            request.body?.includes(characterReferenceId) &&
            request.body?.includes(shotCharacterId)
        )
      ).toBe(true);
    });
  });

  it("submits empty duration as null and allows positive duration", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const durationInput = await screen.findByLabelText(shotCopy.fields.duration);
    await user.clear(durationInput);
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" && request.body?.includes('"duration_seconds":null')
        )
      ).toBe(true);
    });

    await user.clear(durationInput);
    await user.type(durationInput, "4.5");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" && request.body?.includes('"duration_seconds":4.5')
        )
      ).toBe(true);
    });
  });

  it("rejects zero and negative duration before sending a save request", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const durationInput = await screen.findByLabelText(shotCopy.fields.duration);
    await user.clear(durationInput);
    await user.type(durationInput, "0");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒")).toBeInTheDocument();
    expect(requests.some((request) => request.method === "PATCH")).toBe(false);

    await user.clear(durationInput);
    await user.type(durationInput, "-1");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒")).toBeInTheDocument();
    expect(requests.some((request) => request.method === "PATCH")).toBe(false);
  });

  it("keeps form input and does not show success when duration validation fails from the API", async () => {
    const user = userEvent.setup();
    mockShotApi({ failShotUpdate: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const nameInput = await screen.findByLabelText(shotCopy.fields.name);
    const durationInput = screen.getByLabelText(shotCopy.fields.duration);
    await user.clear(nameInput);
    await user.type(nameInput, "保留输入");
    await user.clear(durationInput);
    await user.type(durationInput, "5");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒。")).toBeInTheDocument();
    expect(nameInput).toHaveValue("保留输入");
    expect(durationInput).toHaveValue(5);
    expect(screen.queryByText("镜头已保存")).not.toBeInTheDocument();
  });

  it("opens scene select, filters states by selected scene, and submits scene ids", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      scenes: [scene, secondScene],
      statesByScene: { [sceneId]: [state], [secondSceneId]: [secondState] }
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.sections.scene)).toBeInTheDocument();
    const sceneSelect = screen.getByRole("combobox", { name: shotCopy.fields.scene });
    await user.click(sceneSelect);
    await user.click(await screen.findByRole("option", { name: "Warehouse" }));

    const stateSelect = screen.getByRole("combobox", { name: shotCopy.fields.sceneState });
    await waitFor(() => expect(stateSelect).not.toBeDisabled());
    await user.click(stateSelect);
    expect(await screen.findByRole("option", { name: "Second State" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: state.name })).not.toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Second State" }));
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.body?.includes(secondSceneId) &&
            request.body?.includes(secondStateId)
        )
      ).toBe(true);
    });
  });

  it("opens character select, filters looks by selected character, and adds the shot character", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ characters: [character, secondCharacter] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.sections.characters)).toBeInTheDocument();
    const characterSelect = screen.getAllByRole("combobox", { name: shotCopy.fields.character })[0];
    await user.click(characterSelect);
    await user.click(await screen.findByRole("option", { name: "Second Character" }));

    const lookSelect = screen.getByRole("combobox", { name: shotCopy.fields.look });
    await user.click(lookSelect);
    expect(await screen.findByRole("option", { name: "Second Character Look" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: look.name })).not.toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Second Character Look" }));
    await user.click(screen.getByRole("button", { name: "添加" }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/characters`) &&
            request.body?.includes(secondCharacterId) &&
            request.body?.includes(secondCharacterLook.id)
        )
      ).toBe(true);
    });
  });

  it("shows clear empty and error states for scene and character option requests", async () => {
    mockShotApi({ scenes: [], characters: [] });
    const { unmount } = renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.noScenes)).toBeInTheDocument();
    expect(await screen.findByText(shotCopy.noCharacters)).toBeInTheDocument();

    unmount();
    vi.restoreAllMocks();
    mockShotApi({ failScenes: true, failCharacters: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.scenesLoadFailed)).toBeInTheDocument();
    expect(await screen.findByText(shotCopy.charactersLoadFailed)).toBeInTheDocument();
  });

  it("supports duplicate, move, and delete confirmation", async () => {
    const user = userEvent.setup();
    const secondShot = { ...shot, id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", name: "镜头二", order_index: 2 };
    const { requests } = mockShotApi({ shots: [shot, secondShot] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await screen.findByText("镜头一");
    await user.click(screen.getAllByTitle("复制")[0]);
    await user.click(screen.getAllByTitle("下移")[0]);
    await user.click(screen.getAllByTitle("删除镜头")[0]);
    expect(screen.getByText(/确定删除镜头/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    expect(requests.some((request) => request.url.endsWith("/duplicate"))).toBe(true);
    expect(requests.some((request) => request.url.endsWith("/move"))).toBe(true);
    expect(requests.some((request) => request.method === "DELETE" && request.url.includes(`/shots/${shotId}`))).toBe(true);
  });

  it("binds character and scene references and keeps page structure after API error", async () => {
    const user = userEvent.setup();
    mockShotApi({ failReference: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotRecommendationCopy.tabs.smart)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: shotRecommendationCopy.tabs.character }));
    const referenceButtons = await screen.findAllByRole("button", { name: /身份/ });
    await user.click(referenceButtons[0]);

    expect(await screen.findByText("相同用途的参考图已经绑定。")).toBeInTheDocument();
    expect(screen.getByText("镜头列表")).toBeInTheDocument();
    expect(screen.getByText("镜头信息")).toBeInTheDocument();
  });

  it("shows smart recommendations and binds a suggested character reference", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotRecommendationCopy.description)).toBeInTheDocument();
    expect(await screen.findByText("90 分")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: shotRecommendationCopy.bind })[0]);

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/references`) &&
            request.body?.includes(characterReferenceId) &&
            request.body?.includes('"purpose":"identity"')
        )
      ).toBe(true);
    });
  });

  it("keeps manual tabs usable when smart recommendations fail", async () => {
    const user = userEvent.setup();
    mockShotApi({ failRecommendations: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotRecommendationCopy.loadFailed)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: shotRecommendationCopy.tabs.character }));

    expect((await screen.findAllByText(shotCopy.sections.characterRefs)).length).toBeGreaterThan(0);
  });

  it("disables binding when the suggested purpose is already bound", async () => {
    const boundRecommendations: ShotRecommendationResponse = {
      ...recommendations,
      character_recommendations: [
        {
          ...recommendations.character_recommendations[0],
          items: [
            {
              ...recommendations.character_recommendations[0].items[0],
              bound_purposes: ["identity"],
              is_already_bound_for_suggested_purpose: true
            }
          ]
        }
      ]
    };
    mockShotApi({ recommendations: boundRecommendations });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const boundButtons = await screen.findAllByRole("button", {
      name: shotRecommendationCopy.bound
    });

    expect(boundButtons[0]).toBeDisabled();
  });

  it("keeps scene reference warning copy available for clearing incompatible bindings", async () => {
    const shotWithSceneRef = {
      ...shot,
      references: [
        {
          id: "scene-bound",
          shot_id: shot.id,
          reference_type: "scene" as const,
          character_reference_id: null,
          scene_reference_id: sceneReferenceId,
          shot_character_id: null,
          purpose: "environment",
          order_index: 1,
          notes: null,
          media_asset: mediaAsset,
          character_reference: null,
          scene_reference: sceneReference,
          created_at: "2026-06-28T10:00:00+00:00",
          updated_at: "2026-06-28T10:00:00+00:00"
        }
      ],
      reference_count: 1
    };
    mockShotApi({ shots: [shotWithSceneRef] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText("场景绑定")).toBeInTheDocument();
    expect(shotWithSceneRef.references[0].reference_type).toBe("scene");
  });

  it("shows keyframe task empty state and creates a task without generation", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ shots: [shotWithReferences] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));

    expect(await screen.findByText(keyframeTaskCopy.emptyTitle)).toBeInTheDocument();
    expect(screen.getByText(keyframeTaskCopy.noGeneration)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: keyframeTaskCopy.create }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/keyframe-tasks`)
        )
      ).toBe(true);
    });
  });

  it("edits keyframe task parameters, blocks invalid dimensions, and submits seed zero", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [keyframeTask]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));

    const width = await screen.findByLabelText(keyframeTaskCopy.fields.width);
    await user.clear(width);
    await user.type(width, "250");
    await user.click(screen.getByRole("button", { name: keyframeTaskCopy.save }));

    expect(await screen.findByText("宽度必须在 256 到 4096 之间")).toBeInTheDocument();
    expect(
      requests.some(
        (request) =>
          request.method === "PATCH" &&
          request.url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}`
      )
    ).toBe(false);

    await user.clear(width);
    await user.type(width, "768");
    const seed = screen.getByLabelText(keyframeTaskCopy.fields.seed);
    await user.clear(seed);
    await user.type(seed, "0");
    await user.click(screen.getByRole("button", { name: keyframeTaskCopy.save }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url === `/api/projects/${projectId}/keyframe-tasks/${keyframeTaskId}` &&
            request.body?.includes('"seed":0')
        )
      ).toBe(true);
    });
  });

  it("adds, reorders, and removes keyframe task references from current shot references", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [keyframeTask]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.addReference }));
    const enabledDownButton = screen
      .getAllByTitle("下移")
      .find((button) => !button.hasAttribute("disabled"));
    expect(enabledDownButton).toBeDefined();
    await user.click(enabledDownButton!);
    await user.click(screen.getByTitle("移除参考图"));
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/keyframe-tasks/${keyframeTaskId}/references`) &&
            request.body?.includes(shotCharacterReferenceId)
        )
      ).toBe(true);
    });
    expect(
      requests.some(
        (request) =>
          request.method === "PATCH" &&
          request.url.endsWith(`/references/${keyframeTaskReferenceId}`)
      )
    ).toBe(true);
    expect(
      requests.some(
        (request) =>
          request.method === "DELETE" &&
          request.url.endsWith(`/references/${keyframeTaskReferenceId}`)
      )
    ).toBe(true);
  });

  it("adds keyframe task references through the shot-context asset picker only from existing shot references", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [keyframeTask]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));
    await user.click(await screen.findByRole("button", { name: assetPickerCopy.chooseTaskReference }));
    const candidateButtons = await screen.findAllByRole("button", { name: /reference\.png/ });
    const selectableCandidate = candidateButtons.find((button) => !button.hasAttribute("disabled"));
    expect(selectableCandidate).toBeDefined();
    await user.click(selectableCandidate!);
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/keyframe-tasks/${keyframeTaskId}/references`) &&
            request.body?.includes(shotSceneReferenceId)
        )
      ).toBe(true);
    });
    const request = requests.find(
      (item) =>
        item.method === "POST" &&
        item.url.endsWith(`/keyframe-tasks/${keyframeTaskId}/references`) &&
        item.body?.includes(shotSceneReferenceId)
    );
    expect(request?.body).not.toContain(sceneReferenceId);
  });

  it("keeps manual shot tabs usable when keyframe task loading fails", async () => {
    const user = userEvent.setup();
    mockShotApi({ failKeyframeTasks: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    expect(await screen.findByText(keyframeTaskCopy.loadFailed)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: shotRecommendationCopy.tabs.character }));
    expect((await screen.findAllByText(shotCopy.sections.characterRefs)).length).toBeGreaterThan(0);
  });

  it("shows keyframe generation section and starts a basic workflow run", async () => {
    const user = userEvent.setup();
    const readyTask = { ...keyframeTask, status: "ready" as const };
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [readyTask]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));

    expect(await screen.findByText(keyframeGenerationCopy.noReferenceInputs)).toBeInTheDocument();
    expect(await screen.findByText(keyframeGenerationCopy.providerStatus.online)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: keyframeGenerationCopy.start }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/keyframe-tasks/${keyframeTaskId}/runs`) &&
            request.body?.includes("keyframe_basic_v1")
        )
      ).toBe(true);
    });
  });

  it("creates a video task from a selected keyframe output", async () => {
    const user = userEvent.setup();
    const selectedRun = {
      ...keyframeRun,
      outputs: keyframeRun.outputs.map((output) => ({ ...output, is_selected: true }))
    };
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [keyframeTask],
      keyframeRuns: [selectedRun]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: videoGenerationCopy.useKeyframeOutput }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/video-tasks`) &&
            request.body?.includes(keyframeOutputId)
        )
      ).toBe(true);
    });
  });

  it("shows role-based video frame inputs and uploads an end frame", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      videoTasks: [videoTask]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: "查看 / 编辑" }));
    expect(await screen.findByText(videoGenerationCopy.frameInputs)).toBeInTheDocument();
    expect(screen.getByText(videoGenerationCopy.startFrame)).toBeInTheDocument();
    expect(screen.getByText(videoGenerationCopy.endFrame)).toBeInTheDocument();

    await user.upload(
      screen.getByLabelText(videoGenerationCopy.uploadEndFrame),
      new File(["fake"], "end.png", { type: "image/png" })
    );

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url.endsWith(`/video-tasks/${videoTaskId}`) &&
            request.body?.includes('"role":"end_frame"')
        )
      ).toBe(true);
    });
  });

  it("selects video start and end frames through the asset picker", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      videoTasks: [videoTask],
      keyframeTasks: [keyframeTask],
      keyframeRuns: [keyframeRun]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: "查看 / 编辑" }));
    const pickerButtons = await screen.findAllByRole("button", { name: "从资产选择" });

    await user.click(pickerButtons[0]);
    await user.click(await screen.findByRole("button", { name: /reference\.png/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    const refreshedPickerButtons = await screen.findAllByRole("button", { name: "从资产选择" });
    await user.click(refreshedPickerButtons[1]);
    await user.click(await screen.findByRole("button", { name: /reference\.png/ }));
    await user.click(screen.getByRole("button", { name: assetPickerCopy.confirm }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url.endsWith(`/video-tasks/${videoTaskId}`) &&
            request.body?.includes('"role":"start_frame"') &&
            request.body?.includes(keyframeOutputId)
        )
      ).toBe(true);
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.url.endsWith(`/video-tasks/${videoTaskId}`) &&
            request.body?.includes('"role":"end_frame"') &&
            request.body?.includes(keyframeOutputId)
        )
      ).toBe(true);
    });
  });

  it("keeps role inputs separate when saving video task basics", async () => {
    const payload = videoTaskFormValuesToPayload(
      videoTaskFormSchema.parse({
        name: "视频生成任务",
        prompt: "雨夜街道逐渐推进",
        negative_prompt: "",
        duration_seconds: "5",
        fps: "16",
        width: "768",
        height: "1360",
        seed: "",
        motion_strength: "",
        camera_motion: "",
        workflow_id: "video_i2v_14b_v1"
      })
    );

    expect(payload).not.toHaveProperty("input_media_asset_id");
    expect(payload).not.toHaveProperty("inputs");
    expect(payload.prompt).toBe("雨夜街道逐渐推进");
  });

  it("shows first-last workflow missing end frame readiness without blocking manual controls", async () => {
    const firstLastWorkflow: VideoWorkflow = {
      ...videoWorkflow,
      workflow_id: "video_wan22_14b_flf2v_v1",
      display_name: "Wan2.2 首尾帧视频",
      mode: "first_last_frame_to_video",
      required_input_roles: ["start_frame", "end_frame"],
      available: false,
      missing_requirements: ["workflow_file_missing"]
    };
    const firstLastTask: VideoTask = {
      ...videoTask,
      workflow_id: firstLastWorkflow.workflow_id,
      readiness: {
        readiness_status: "incomplete",
        blocking_issues: ["missing_end_frame", "workflow_unavailable"],
        warnings: []
      }
    };
    mockShotApi({
      shots: [shotWithReferences],
      videoTasks: [firstLastTask],
      videoWorkflows: [firstLastWorkflow]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await userEvent.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await userEvent.click(await screen.findByRole("button", { name: "查看 / 编辑" }));

    expect(
      await screen.findByText((text) =>
        text.includes(videoGenerationCopy.blockingIssues.missing_end_frame)
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText((text) =>
        text.includes(videoGenerationCopy.disabledReasons.workflowUnavailable)
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: videoGenerationCopy.start })).toBeDisabled();
    expect(screen.getByRole("button", { name: videoGenerationCopy.save })).toBeEnabled();
  });

  it("saves Wan first-last video task fields before marking ready and starting", async () => {
    const user = userEvent.setup();
    const firstLastWorkflow: VideoWorkflow = {
      ...videoWorkflow,
      workflow_id: "video_wan22_14b_flf2v_v1",
      display_name: "Wan2.2 14B 首尾帧视频",
      version: "0.2.0",
      mode: "first_last_frame_to_video",
      required_input_roles: ["start_frame", "end_frame"],
      available: true,
      missing_requirements: []
    };
    const firstLastTask: VideoTask = {
      ...videoTask,
      prompt: null,
      negative_prompt: null,
      duration_seconds: 2,
      fps: 16,
      width: 640,
      height: 640,
      seed: null,
      motion_strength: null,
      camera_motion: null,
      workflow_id: firstLastWorkflow.workflow_id,
      inputs: [
        ...videoTask.inputs,
        {
          id: "video-input-end",
          role: "end_frame",
          media_asset_id: mediaAsset.id,
          source_keyframe_output_id: null,
          source_keyframe_task_id: null,
          sort_order: 2,
          media_asset: mediaAsset,
          created_at: "2026-06-28T10:00:00+00:00",
          updated_at: "2026-06-28T10:00:00+00:00"
        }
      ],
      readiness: {
        readiness_status: "incomplete",
        blocking_issues: ["missing_prompt", "workflow_unavailable"],
        warnings: []
      }
    };
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      videoTasks: [firstLastTask],
      videoWorkflows: [firstLastWorkflow]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: "查看 / 编辑" }));
    expect(await screen.findByText(/v0\.2\.0/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: videoGenerationCopy.start })).toBeDisabled();

    await user.type(screen.getByLabelText(videoGenerationCopy.fields.prompt), "cinematic rain push in");
    await user.type(screen.getByLabelText(videoGenerationCopy.fields.negativePrompt), "bad quality");
    await user.clear(screen.getByLabelText(videoGenerationCopy.fields.seed));
    await user.type(screen.getByLabelText(videoGenerationCopy.fields.seed), "12345");
    await user.clear(screen.getByLabelText(videoGenerationCopy.fields.motionStrength));
    await user.type(screen.getByLabelText(videoGenerationCopy.fields.motionStrength), "0.45");
    const cameraMotionInputs = screen.getAllByLabelText(videoGenerationCopy.fields.cameraMotion);
    await user.type(cameraMotionInputs[cameraMotionInputs.length - 1], "slow cinematic push-in");
    await user.click(screen.getByRole("button", { name: videoGenerationCopy.save }));

    await waitFor(() => {
      const saveRequest = requests.find(
        (request) =>
          request.method === "PATCH" &&
          request.url.endsWith(`/video-tasks/${videoTaskId}`)
      );
      expect(saveRequest).toBeTruthy();
      const payload = JSON.parse(saveRequest?.body ?? "{}");
      expect(payload).toMatchObject({
        prompt: "cinematic rain push in",
        negative_prompt: "bad quality",
        workflow_id: "video_wan22_14b_flf2v_v1",
        duration_seconds: 2,
        fps: 16,
        width: 640,
        height: 640,
        seed: 12345,
        motion_strength: 0.45,
        camera_motion: "slow cinematic push-in"
      });
      expect(payload).not.toHaveProperty("inputs");
    });

    await user.click(screen.getByRole("button", { name: videoGenerationCopy.markReady }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: videoGenerationCopy.start })).toBeEnabled()
    );
  });

  it("starts a ready video task, renders video output, and selects a version", async () => {
    const user = userEvent.setup();
    const readyVideoTask = {
      ...videoTask,
      status: "ready" as const,
      readiness: { readiness_status: "ready" as const, blocking_issues: [], warnings: [] }
    };
    const availableVideoWorkflow = {
      ...videoWorkflow,
      available: true,
      missing_requirements: []
    };
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      videoTasks: [readyVideoTask],
      videoWorkflows: [availableVideoWorkflow],
      videoRuns: [videoRun]
    });
    const { container } = renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: "查看 / 编辑" }));
    expect(await screen.findByText(videoGenerationCopy.outputGallery)).toBeInTheDocument();
    expect(document.querySelector("video")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: videoGenerationCopy.start }));
    await user.click(screen.getByRole("button", { name: videoGenerationCopy.useVersion }));
    await waitFor(() => expect(screen.getByRole("button", { name: videoGenerationCopy.unselect })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: videoGenerationCopy.unselect }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/video-tasks/${videoTaskId}/runs`) &&
            request.body?.includes("video_i2v_14b_v1")
        )
      ).toBe(true);
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/video-outputs/${videoOutputId}/select`)
        )
      ).toBe(true);
      expect(
        requests.some(
          (request) =>
            request.method === "DELETE" &&
            request.url.endsWith(`/video-outputs/${videoOutputId}/select`)
        )
      ).toBe(true);
    });
    expect(container).toBeDefined();
  });

  it("explains why basic workflow generation is disabled for output count greater than one", async () => {
    const user = userEvent.setup();
    const readyTask = { ...keyframeTask, status: "ready" as const, output_count: 2 };
    mockShotApi({ shots: [shotWithReferences], keyframeTasks: [readyTask] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));

    expect(
      await screen.findByText(keyframeGenerationCopy.disabledReasons.outputCountUnsupported)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: keyframeGenerationCopy.start })).toBeDisabled();
  });

  it("disables generation when provider is offline or a run is active", async () => {
    const user = userEvent.setup();
    const readyTask = { ...keyframeTask, status: "ready" as const };
    const offlineCapabilities: SystemCapabilities = {
      ...systemCapabilities,
      keyframe_generation: { available: false, provider: "comfyui", status: "offline" }
    };
    mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [readyTask],
      capabilities: offlineCapabilities
    });

    const { unmount } = renderRoute(`/projects/${projectId}/shots/${shotId}`);
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));
    expect(await screen.findByText(keyframeGenerationCopy.disabledReasons.providerOffline)).toBeInTheDocument();
    unmount();
    vi.restoreAllMocks();

    mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [readyTask],
      keyframeRuns: [{ ...keyframeRun, status: "running", outputs: [] }]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));
    expect(await screen.findByText(keyframeGenerationCopy.disabledReasons.activeRun)).toBeInTheDocument();
  });

  it("shows generated outputs and toggles selected version", async () => {
    const user = userEvent.setup();
    const readyTask = { ...keyframeTask, status: "ready" as const };
    const { requests } = mockShotApi({
      shots: [shotWithReferences],
      keyframeTasks: [readyTask],
      keyframeRuns: [keyframeRun]
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.tab }));
    await user.click(await screen.findByRole("button", { name: keyframeTaskCopy.edit }));
    await screen.findByText(keyframeGenerationCopy.outputGallery);
    await user.click(screen.getByRole("button", { name: keyframeGenerationCopy.useVersion }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/keyframe-outputs/${keyframeOutputId}/select`)
        )
      ).toBe(true);
    });
  });
});
