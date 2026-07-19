import type { Character } from "@/features/characters/types";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import type { ProjectProductionStatus, ShotProductionStatus } from "@/features/production-status/types";
import type { Scene } from "@/features/scenes/types";
import type { Shot } from "@/features/shots/types";
import type { ProjectTimeline } from "@/features/timeline/types";

import { countAdoptedSteps } from "./recommendation";

export type StudioStageStatus = "completed" | "current" | "not_started" | "blocked";

export interface StudioStage {
  key: "assets" | "shots" | "keyframes" | "video" | "export";
  title: string;
  status: StudioStageStatus;
  detail: string;
}

export interface StudioIssue {
  key: string;
  title: string;
  detail: string;
  tone: "warning" | "danger" | "info";
}

export interface StudioRecentItem {
  id: string;
  title: string;
  label: string;
  href: string;
  updatedAt: string;
}

export function buildStudioStages(input: {
  characterCount: number;
  sceneCount: number;
  shotCount: number;
  productionStatus: ProjectProductionStatus | null;
  timeline: ProjectTimeline | null;
}): StudioStage[] {
  const adopted = countAdoptedSteps(input.productionStatus);
  const blocked = (input.productionStatus?.summary.blocked ?? 0) > 0;
  const assetsReady = input.characterCount > 0 && input.sceneCount > 0;
  const keyframesReady = input.shotCount > 0 && adopted.firstFrame >= input.shotCount && adopted.endFrame >= input.shotCount;
  const videoReady = input.shotCount > 0 && adopted.video >= input.shotCount;

  return [
    {
      key: "assets",
      title: "素材准备",
      status: assetsReady ? "completed" : "current",
      detail: `${input.characterCount} 个角色 / ${input.sceneCount} 个场景`
    },
    {
      key: "shots",
      title: "镜头规划",
      status: input.shotCount > 0 ? "completed" : assetsReady ? "current" : "not_started",
      detail: `${input.shotCount} 个镜头`
    },
    {
      key: "keyframes",
      title: "关键帧",
      status: blocked ? "blocked" : keyframesReady ? "completed" : input.shotCount > 0 ? "current" : "not_started",
      detail: `首帧 ${adopted.firstFrame} / 尾帧 ${adopted.endFrame}`
    },
    {
      key: "video",
      title: "视频生成",
      status: blocked ? "blocked" : videoReady ? "completed" : keyframesReady ? "current" : "not_started",
      detail: `已采用视频 ${adopted.video}`
    },
    {
      key: "export",
      title: "成片导出",
      status: input.timeline?.exportable ? "current" : videoReady ? "current" : "not_started",
      detail: input.timeline?.exportable ? "时间线可导出" : "等待采用视频"
    }
  ];
}

export function buildStudioIssues(input: {
  apiAvailable: boolean;
  comfyUiAvailable: boolean;
  videoAvailable: boolean;
  productionStatus: ProjectProductionStatus | null;
  generationTasks: GenerationTaskSummary[];
  timeline: ProjectTimeline | null;
}): StudioIssue[] {
  const issues: StudioIssue[] = [];
  if (!input.apiAvailable) {
    issues.push({ key: "api", title: "后端不可用", detail: "请检查本地 FastAPI 服务是否运行。", tone: "danger" });
  }
  if (!input.comfyUiAvailable) {
    issues.push({ key: "comfyui", title: "ComfyUI 不可用", detail: "关键帧或视频生成前需要本地 ComfyUI 在线。", tone: "warning" });
  }
  if (!input.videoAvailable) {
    issues.push({ key: "video", title: "视频工作流不可用", detail: "视频生成所需模型或节点尚未就绪，不影响关键帧功能。", tone: "warning" });
  }

  for (const task of input.generationTasks) {
    if (task.latest_run_status === "failed" || task.latest_run_status === "interrupted") {
      issues.push({
        key: `task-${task.task_id}`,
        title: `${task.shot_name} / ${task.task_name}`,
        detail: "最近一次生成失败或被中断。",
        tone: "danger"
      });
    }
  }

  for (const blocker of input.timeline?.blockers ?? []) {
    issues.push({
      key: `timeline-${blocker.code}-${blocker.shot_id ?? "project"}`,
      title: "时间线阻塞",
      detail: blocker.message,
      tone: "warning"
    });
  }

  return issues;
}

export function buildRecentItems(input: {
  projectId: string;
  characters: Character[];
  scenes: Scene[];
  shots: Shot[];
  tasks: GenerationTaskSummary[];
}): StudioRecentItem[] {
  const characterItems = input.characters.map((item) => ({
    id: `character-${item.id}`,
    title: item.name,
    label: "角色",
    href: `/projects/${input.projectId}/characters/${item.id}`,
    updatedAt: item.updated_at
  }));
  const sceneItems = input.scenes.map((item) => ({
    id: `scene-${item.id}`,
    title: item.name,
    label: "场景",
    href: `/projects/${input.projectId}/scenes/${item.id}`,
    updatedAt: item.updated_at
  }));
  const shotItems = input.shots.map((item) => ({
    id: `shot-${item.id}`,
    title: item.name,
    label: "镜头",
    href: `/projects/${input.projectId}/studio?shotId=${item.id}&intent=inspect`,
    updatedAt: item.updated_at
  }));
  const taskItems = input.tasks.map((item) => ({
    id: `task-${item.task_id}`,
    title: item.task_name,
    label: item.task_type === "keyframe" ? "关键帧任务" : "视频任务",
    href: `/projects/${input.projectId}/shots/${item.shot_id}`,
    updatedAt: item.updated_at
  }));

  return [...characterItems, ...sceneItems, ...shotItems, ...taskItems]
    .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt) || left.id.localeCompare(right.id))
    .slice(0, 5);
}

export function findProductionShot(
  productionStatus: ProjectProductionStatus | null,
  shotId: string | null
): ShotProductionStatus | null {
  if (!shotId) {
    return null;
  }
  return (productionStatus?.items ?? productionStatus?.shots ?? []).find((item) => item.shot_id === shotId) ?? null;
}
