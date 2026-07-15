import type {
  ProductionAction,
  ProductionAssetStep,
  ProductionDirectorPromptStep,
  ProductionFrameStep,
  ProductionOverallStatus,
  ProductionVideoStep,
  ShotProductionStatus
} from "./types";

const defaultAssetStep: Required<ProductionAssetStep> = {
  status: "missing",
  character_count: 0,
  reference_count: 0,
  has_primary_subject: false,
  has_scene: false,
  has_scene_state: false,
  scene_name: null,
  scene_state_name: null,
  warnings: []
};

const defaultDirectorPromptStep: Required<ProductionDirectorPromptStep> = {
  status: "not_created",
  director_template_available: false,
  recommended_template_id: null
};

const defaultFrameStep: Required<ProductionFrameStep> = {
  status: "not_created",
  task_id: null,
  task_name: null,
  adopted_output_id: null,
  adopted_media_asset_id: null,
  content_url: null
};

const defaultVideoStep: Required<ProductionVideoStep> = {
  status: "not_created",
  task_id: null,
  task_name: null,
  adopted_output_id: null,
  adopted_media_asset_id: null,
  content_url: null,
  has_start_frame: false,
  has_end_frame: false
};

export function normalizeShotProductionStatus(status: ShotProductionStatus) {
  const steps = status.steps ?? {};
  const assets = { ...defaultAssetStep, ...(steps.assets ?? {}) };
  const directorPrompt = { ...defaultDirectorPromptStep, ...(steps.director_prompt ?? {}) };
  const firstFrame = { ...defaultFrameStep, ...(steps.first_frame ?? {}) };
  const endFrame = { ...defaultFrameStep, ...(steps.end_frame ?? {}) };
  const video = { ...defaultVideoStep, ...(steps.video ?? {}) };
  const finalAdoption =
    steps.final_adoption ??
    (video.status === "adopted"
      ? { ...video, status: "adopted" as const }
      : { ...defaultVideoStep });

  return {
    shotId: status.shot_id,
    shotName: status.shot_name ?? "未命名镜头",
    orderIndex: status.order_index ?? 0,
    overallStatus: (status.overall_status ?? "blocked") as ProductionOverallStatus,
    steps: {
      assets,
      director_prompt: directorPrompt,
      first_frame: firstFrame,
      end_frame: endFrame,
      video,
      final_adoption: { ...defaultVideoStep, ...finalAdoption }
    },
    blockers: Array.isArray(status.blockers) ? status.blockers : [],
    nextActions: Array.isArray(status.next_actions)
      ? (status.next_actions as ProductionAction[])
      : [],
    continuityCandidate: status.continuity_candidate ?? null
  };
}
