import type { GenerationRunStatus, GenerationTaskType } from "./types";

export const generationTaskCopy = {
  title: "生成中心",
  description: "项目级查看关键帧任务和视频任务。这里不会自动触发生成。",
  emptyTitle: "暂无生成任务",
  emptyDescription: "在镜头工作台中创建关键帧或视频任务后，会集中显示在这里。",
  loadFailed: "生成任务加载失败，请稍后重试。",
  filters: {
    all: "全部",
    keyframe: "关键帧",
    video: "视频",
    draft: "草稿",
    ready: "就绪",
    running: "生成中",
    completed: "已完成",
    failed: "失败"
  },
  taskType: {
    keyframe: "关键帧",
    video: "视频"
  } satisfies Record<GenerationTaskType, string>,
  taskStatus: {
    draft: "草稿",
    ready: "就绪"
  },
  runStatus: {
    queued: "排队中",
    running: "生成中",
    completed: "已完成",
    failed: "失败",
    cancelled: "已中断",
    interrupted: "已中断"
  } satisfies Record<GenerationRunStatus, string>,
  selected: "已采用",
  unselected: "未采用",
  hasOutput: "已有输出",
  noOutput: "暂无输出",
  openShot: "打开镜头",
  latestRun: "最新运行",
  noRun: "尚未运行",
  workflowUnset: "未选择工作流"
};
