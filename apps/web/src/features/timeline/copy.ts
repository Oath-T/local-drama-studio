import type { ProjectExportStatus, TimelineClipStatus } from "./types";

export const timelineCopy = {
  title: "时间线与导出",
  description:
    "按镜头顺序检查已采用的视频输出，并在本地 FFmpeg 可用时导出最终成片。",
  refresh: "刷新",
  createExport: "创建导出草稿",
  markReady: "标记可导出",
  startExport: "开始导出",
  openShot: "打开镜头",
  download: "下载最终视频",
  emptyTimelineTitle: "暂无镜头",
  emptyTimelineDescription: "请先在镜头工作台创建镜头，并为每个镜头采用视频输出。",
  noBlockers: "当前没有阻断项。",
  blockersTitle: "导出前检查",
  ffmpegReady: "FFmpeg / FFprobe 已可用",
  ffmpegUnavailable: "未检测到 FFmpeg / FFprobe，暂不能导出最终成片。",
  exportHistory: "导出历史",
  noExportsTitle: "暂无导出任务",
  noExportsDescription: "时间线满足条件后，可以创建第一个最终成片导出草稿。",
  finalOutput: "最终视频",
  noOutput: "暂无最终视频输出",
  status: {
    draft: "草稿",
    ready: "就绪",
    queued: "排队中",
    running: "导出中",
    completed: "已完成",
    failed: "失败"
  } satisfies Record<ProjectExportStatus, string>,
  clipStatus: {
    ready: "已采用",
    missing: "缺少采用视频",
    blocked: "不可用"
  } satisfies Record<TimelineClipStatus, string>
};
