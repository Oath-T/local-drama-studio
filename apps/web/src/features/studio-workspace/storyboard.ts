import type {
  ProjectProductionStatus,
  ProductionFrameStep,
  ProductionVideoStep,
  ShotProductionStatus,
  VideoStepStatus
} from "@/features/production-status/types";
import type { Shot } from "@/features/shots/types";

export interface StoryboardMediaPreview {
  status: "adopted" | "completed" | "running" | "failed" | "not_created" | "unavailable";
  label: string;
  contentUrl: string | null;
  kind: "image" | "video";
}

export interface StoryboardShotItem {
  shot: Shot;
  production: ShotProductionStatus | null;
  firstFramePreview: StoryboardMediaPreview;
  endFramePreview: StoryboardMediaPreview;
  videoPreview: StoryboardMediaPreview;
}

export function getStoryboardProductionItems(
  status: ProjectProductionStatus | null
): ShotProductionStatus[] {
  return status?.items ?? status?.shots ?? [];
}

function isRunningStatus(status: string | undefined) {
  return status === "queued" || status === "running";
}

function hasFailure(production: ShotProductionStatus | null) {
  const blockerText = (production?.blockers ?? []).join(" ").toLowerCase();
  return ["failed", "failure", "error", "interrupted", "timeout", "失败", "中断", "超时"].some(
    (keyword) => blockerText.includes(keyword)
  );
}

function framePreview(step: ProductionFrameStep | undefined, label: "首帧" | "尾帧"): StoryboardMediaPreview {
  if (!step) {
    return { status: "not_created", label: `${label}未生成`, contentUrl: null, kind: "image" };
  }

  if (step.status === "adopted") {
    return { status: "adopted", label: `${label}已采用`, contentUrl: step.content_url, kind: "image" };
  }

  if (step.status === "completed") {
    return { status: "completed", label: `${label}待采用`, contentUrl: step.content_url, kind: "image" };
  }

  if (step.status === "running" || step.status === "ready") {
    return { status: "running", label: `${label}生成中`, contentUrl: null, kind: "image" };
  }

  if (step.status === "draft") {
    return { status: "not_created", label: `${label}草稿`, contentUrl: null, kind: "image" };
  }

  return { status: "not_created", label: `${label}未生成`, contentUrl: null, kind: "image" };
}

function videoLabel(status: VideoStepStatus | undefined, videoAvailable: boolean, failed: boolean) {
  if (failed) return "视频生成失败";
  if (status === "adopted") return "视频已采用";
  if (isRunningStatus(status)) return "视频生成中";
  if (status === "completed") return "视频待采用";
  if (!videoAvailable) return "视频能力不可用";
  return "视频未生成";
}

function videoPreview(
  step: ProductionVideoStep | undefined,
  videoAvailable: boolean,
  failed: boolean
): StoryboardMediaPreview {
  const label = videoLabel(step?.status, videoAvailable, failed);

  if (label === "视频已采用") {
    return { status: "adopted", label, contentUrl: step?.content_url ?? null, kind: "video" };
  }

  if (label === "视频待采用") {
    return { status: "completed", label, contentUrl: step?.content_url ?? null, kind: "video" };
  }

  if (label === "视频生成中") {
    return { status: "running", label, contentUrl: null, kind: "video" };
  }

  if (label === "视频生成失败") {
    return { status: "failed", label, contentUrl: null, kind: "video" };
  }

  if (label === "视频能力不可用") {
    return { status: "unavailable", label, contentUrl: null, kind: "video" };
  }

  return { status: "not_created", label, contentUrl: null, kind: "video" };
}

export function buildStoryboardShotItems({
  shots,
  productionStatus,
  videoAvailable
}: {
  shots: Shot[];
  productionStatus: ProjectProductionStatus | null;
  videoAvailable: boolean;
}): StoryboardShotItem[] {
  const productionByShotId = new Map(
    getStoryboardProductionItems(productionStatus).map((item) => [item.shot_id, item])
  );

  return [...shots]
    .sort((a, b) => a.order_index - b.order_index || a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id))
    .map((shot) => {
      const production = productionByShotId.get(shot.id) ?? null;
      const failed = hasFailure(production);
      return {
        shot,
        production,
        firstFramePreview: framePreview(production?.steps.first_frame, "首帧"),
        endFramePreview: framePreview(production?.steps.end_frame, "尾帧"),
        videoPreview: videoPreview(production?.steps.video, videoAvailable, failed)
      };
    });
}
