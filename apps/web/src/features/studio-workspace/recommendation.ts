import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import type { ProjectProductionStatus, ShotProductionStatus } from "@/features/production-status/types";
import type { Shot } from "@/features/shots/types";

export type StudioRecommendationKind =
  | "create_character"
  | "create_scene"
  | "create_shot"
  | "generate_first_frame"
  | "generate_end_frame"
  | "generate_video"
  | "check_video_config"
  | "review_failed_tasks"
  | "continue_next_shot"
  | "preview_final";

export interface StudioRecommendationInput {
  projectId: string;
  characterCount: number;
  sceneCount: number;
  shots: Shot[];
  productionStatus: ProjectProductionStatus | null;
  generationTasks: GenerationTaskSummary[];
  videoGenerationAvailable: boolean;
}

export interface StudioRecommendation {
  kind: StudioRecommendationKind;
  title: string;
  reason: string;
  href: string;
  shotId: string | null;
  intent: "create" | "inspect" | "generate" | "review" | "export";
}

function orderedProductionShots(productionStatus: ProjectProductionStatus | null) {
  return [...(productionStatus?.items ?? productionStatus?.shots ?? [])].sort(
    (left, right) => left.order_index - right.order_index || left.shot_id.localeCompare(right.shot_id)
  );
}

function hasFailedOrBlockingTask(tasks: GenerationTaskSummary[]) {
  return tasks.some((task) => task.latest_run_status === "failed" || task.latest_run_status === "interrupted");
}

function findFirstIncompleteShot(items: ShotProductionStatus[]) {
  return items.find((item) => item.steps.video?.status !== "adopted") ?? null;
}

export function buildStudioRecommendation(input: StudioRecommendationInput): StudioRecommendation {
  const { projectId } = input;

  if (input.characterCount === 0) {
    return {
      kind: "create_character",
      title: "创建第一个角色",
      reason: "项目还没有可调用人物资产，先建立主角或关键配角。",
      href: `/projects/${projectId}/characters`,
      shotId: null,
      intent: "create"
    };
  }

  if (input.sceneCount === 0) {
    return {
      kind: "create_scene",
      title: "创建第一个场景",
      reason: "已有角色，但还没有场景资产。先建立故事发生地点。",
      href: `/projects/${projectId}/scenes`,
      shotId: null,
      intent: "create"
    };
  }

  if (input.shots.length === 0) {
    return {
      kind: "create_shot",
      title: "创建第一个镜头",
      reason: "角色和场景已就绪，下一步可以开始规划镜头。",
      href: `/projects/${projectId}/shots`,
      shotId: null,
      intent: "create"
    };
  }

  const productionShots = orderedProductionShots(input.productionStatus);
  const targetShot = findFirstIncompleteShot(productionShots);

  if (targetShot?.steps.first_frame?.status !== undefined && targetShot.steps.first_frame.status !== "adopted") {
    return {
      kind: "generate_first_frame",
      title: "生成首帧",
      reason: `镜头 ${targetShot.order_index}「${targetShot.shot_name}」尚未采用首帧。`,
      href: `/projects/${projectId}/studio?shotId=${targetShot.shot_id}&intent=generate`,
      shotId: targetShot.shot_id,
      intent: "generate"
    };
  }

  if (
    targetShot?.steps.first_frame?.status === "adopted" &&
    targetShot.steps.end_frame?.status !== "adopted"
  ) {
    return {
      kind: "generate_end_frame",
      title: "生成尾帧",
      reason: `镜头 ${targetShot.order_index}「${targetShot.shot_name}」已有首帧，但尚未采用尾帧。`,
      href: `/projects/${projectId}/studio?shotId=${targetShot.shot_id}&intent=generate`,
      shotId: targetShot.shot_id,
      intent: "generate"
    };
  }

  if (
    targetShot?.steps.first_frame?.status === "adopted" &&
    targetShot.steps.end_frame?.status === "adopted" &&
    targetShot.steps.video?.status !== "adopted"
  ) {
    if (input.videoGenerationAvailable) {
      return {
        kind: "generate_video",
        title: "生成视频",
        reason: `镜头 ${targetShot.order_index} 已有首帧和尾帧，可以进入首尾帧视频生成。`,
        href: `/projects/${projectId}/studio?shotId=${targetShot.shot_id}&intent=generate`,
        shotId: targetShot.shot_id,
        intent: "generate"
      };
    }

    return {
      kind: "check_video_config",
      title: "检查视频生成配置",
      reason: "镜头已具备首尾帧，但当前视频工作流或模型尚不可用。",
      href: `/projects/${projectId}/generation`,
      shotId: targetShot.shot_id,
      intent: "review"
    };
  }

  if (hasFailedOrBlockingTask(input.generationTasks) || (input.productionStatus?.summary.blocked ?? 0) > 0) {
    return {
      kind: "review_failed_tasks",
      title: "查看失败原因",
      reason: "项目中存在失败或阻塞的生成任务，建议先处理问题再继续生产。",
      href: `/projects/${projectId}/generation`,
      shotId: null,
      intent: "review"
    };
  }

  const nextShot = productionShots.find((item) => item.overall_status !== "completed") ?? null;
  if (nextShot) {
    return {
      kind: "continue_next_shot",
      title: "继续下一个未完成镜头",
      reason: `镜头 ${nextShot.order_index}「${nextShot.shot_name}」仍有生产步骤未完成。`,
      href: `/projects/${projectId}/studio?shotId=${nextShot.shot_id}&intent=inspect`,
      shotId: nextShot.shot_id,
      intent: "inspect"
    };
  }

  return {
    kind: "preview_final",
    title: "预览成片时间线",
    reason: "所有镜头都已有采用视频，可以进入时间线检查最终导出。",
    href: `/projects/${projectId}/timeline`,
    shotId: null,
    intent: "export"
  };
}

export function countAdoptedSteps(productionStatus: ProjectProductionStatus | null) {
  const shots = orderedProductionShots(productionStatus);
  return {
    firstFrame: shots.filter((shot) => shot.steps.first_frame?.status === "adopted").length,
    endFrame: shots.filter((shot) => shot.steps.end_frame?.status === "adopted").length,
    video: shots.filter((shot) => shot.steps.video?.status === "adopted").length
  };
}
