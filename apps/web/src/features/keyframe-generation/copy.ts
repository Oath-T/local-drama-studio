import type { KeyframeRunStatus } from "./types";

export const keyframeGenerationCopy = {
  title: "关键帧生成",
  provider: "ComfyUI 状态",
  workflow: "固定工作流",
  start: "开始生成",
  starting: "正在提交",
  retry: "重新生成",
  useVersion: "采用此版本",
  selected: "已采用",
  unselect: "取消采用",
  openOriginal: "打开原图",
  download: "下载",
  runList: "生成记录",
  outputGallery: "生成结果",
  noRuns: "当前任务还没有生成记录。",
  noOutputs: "当前生成记录还没有输出图片。",
  localOnly: "生成由本机后端提交到本地 ComfyUI，前端不会直连 ComfyUI。",
  noReferenceInputs:
    "当前基础工作流仅使用提示词和生成参数，不使用任务中的参考图。",
  promptLanguage: {
    zh: "本次将使用中文提示词。",
    en: "本次将使用英文提示词。"
  },
  providerStatus: {
    online: "ComfyUI 已连接",
    offline: "ComfyUI 未连接",
    unconfigured: "关键帧生成服务尚未配置"
  },
  status: {
    queued: "等待生成",
    running: "正在生成",
    completed: "生成完成",
    failed: "生成失败",
    cancelled: "已取消",
    interrupted: "执行中断"
  } satisfies Record<KeyframeRunStatus, string>,
  disabledReasons: {
    notReadyStatus: "任务尚未标记为准备完成。",
    notReadyReadiness: "任务仍有阻断项未处理。",
    outputCountUnsupported: "当前基础工作流仅支持单次生成一张图片，请将输出数量调整为 1。",
    providerOffline: "ComfyUI 未连接。",
    workflowMissing: "请选择可用工作流。",
    workflowUnavailable: "当前工作流不可用。",
    activeRun: "当前任务已有生成正在执行。"
  },
  missingRequirements: {
    provider_offline: "ComfyUI 未连接",
    default_checkpoint_not_configured: "工作流依赖的模型尚未配置",
    required_node_types_unavailable: "无法确认 ComfyUI 节点能力"
  },
  generated: "生成任务已提交。",
  retryStarted: "已创建新的生成记录。",
  selectUpdated: "采用版本已更新。",
  selectFailed: "采用版本更新失败。",
  startFailed: "提交生成任务失败。",
  loadFailed: "生成记录加载失败。",
  workflowLoadFailed: "工作流加载失败。",
  capabilitiesLoadFailed: "生成服务状态加载失败。"
};

export function missingRequirementText(value: string): string {
  if (value.startsWith("node_type_missing:")) {
    return `缺少节点：${value.replace("node_type_missing:", "")}`;
  }
  return (
    keyframeGenerationCopy.missingRequirements[
      value as keyof typeof keyframeGenerationCopy.missingRequirements
    ] ?? value
  );
}
