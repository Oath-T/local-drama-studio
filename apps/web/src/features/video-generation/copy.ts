import type {
  VideoRunStatus,
  VideoTaskBlockingIssue,
  VideoTaskReadinessStatus,
  VideoTaskStatus,
  VideoTaskWarning
} from "./types";

export const videoGenerationCopy = {
  title: "视频生成",
  description: "使用本地 ComfyUI 将一张已选图片转为短视频。结果通过本平台媒体接口读取，不暴露本地路径或 ComfyUI 地址。",
  localOnly: "本轮只支持本地 ComfyUI 图生视频任务，不下载模型、不安装 Custom Node、不自动批量生成。",
  create: "新建视频任务",
  creating: "正在创建",
  edit: "编辑视频任务",
  save: "保存任务",
  saving: "正在保存",
  delete: "删除视频任务",
  deleted: "视频任务已删除",
  deleteDescription: (name: string) => `确定删除视频任务“${name}”吗？已有运行记录和输出会随任务一起移除。`,
  markReady: "标记就绪",
  markDraft: "退回草稿",
  markedReady: "视频任务已标记为就绪",
  markedDraft: "视频任务已退回草稿",
  saved: "视频任务已保存",
  created: "视频任务已创建",
  start: "开始生成",
  starting: "正在提交",
  generated: "视频生成已提交",
  startFailed: "视频生成提交失败",
  loadFailed: "视频任务加载失败，关键帧和手动资产仍可继续使用。",
  workflowLoadFailed: "视频工作流加载失败",
  capabilitiesLoadFailed: "生成服务状态加载失败",
  noTasks: "当前镜头还没有视频生成任务",
  noTasksDescription: "可以从已选关键帧或上传一张项目图片开始图生视频。",
  noRuns: "当前任务还没有运行记录",
  noOutputs: "当前还没有视频输出",
  outputGallery: "视频输出",
  runList: "运行记录",
  uploadInput: "上传起始图",
  uploadStartFrame: "上传起始帧",
  uploadEndFrame: "上传结束帧",
  uploadFailed: "起始图上传失败",
  useKeyframeOutput: "使用已选关键帧",
  useAsStartFrame: "设为起始帧",
  useAsEndFrame: "设为结束帧",
  noKeyframeOutput: "当前镜头还没有已选关键帧，可先在关键帧任务中选择输出，或上传项目图片。",
  inputImage: "起始图",
  frameInputs: "关键帧输入",
  frameInputDescription: "按工作流要求选择起始帧和结束帧。旧任务的单张输入会作为起始帧继续使用。",
  startFrame: "起始帧",
  endFrame: "结束帧",
  noFrameImage: "尚未选择图片",
  workflow: "工作流",
  selected: "已选版本",
  selectUpdated: "已选视频已更新",
  selectFailed: "视频选择失败",
  useVersion: "设为本镜头视频",
  unselect: "取消选择",
  download: "下载",
  openOriginal: "打开",
  providerStatus: {
    online: "ComfyUI 已连接",
    offline: "ComfyUI 未连接",
    unconfigured: "生成服务未配置"
  },
  status: {
    draft: "草稿",
    ready: "就绪"
  } satisfies Record<VideoTaskStatus, string>,
  runStatus: {
    queued: "排队中",
    running: "生成中",
    completed: "已完成",
    failed: "失败",
    interrupted: "已中断"
  } satisfies Record<VideoRunStatus, string>,
  readiness: {
    ready: "可以生成",
    incomplete: "尚未就绪"
  } satisfies Record<VideoTaskReadinessStatus, string>,
  fields: {
    name: "任务名称",
    prompt: "视频提示词",
    negativePrompt: "反向提示词",
    duration: "时长（秒）",
    fps: "帧率",
    width: "宽度",
    height: "高度",
    seed: "随机种子",
    motionStrength: "运动强度",
    cameraMotion: "镜头运动"
  },
  blockingIssues: {
    missing_name: "缺少任务名称",
    missing_input_image: "缺少起始图",
    missing_start_frame: "缺少起始帧",
    missing_end_frame: "缺少结束帧",
    input_image_unavailable: "起始图不可用",
    start_frame_unavailable: "起始帧不可用",
    end_frame_unavailable: "结束帧不可用",
    input_image_not_image: "起始图必须是图片",
    start_frame_not_image: "起始帧必须是图片",
    end_frame_not_image: "结束帧必须是图片",
    missing_prompt: "缺少视频提示词",
    invalid_duration: "时长必须大于 0",
    invalid_fps: "帧率必须大于 0",
    invalid_dimensions: "尺寸必须在 256 到 2048 之间，且为 8 的倍数",
    invalid_seed: "随机种子必须为空或非负整数",
    workflow_not_selected: "未选择工作流",
    workflow_unavailable: "工作流当前不可用",
    workflow_requires_end_frame: "首尾帧工作流必须声明结束帧输入"
  } satisfies Record<VideoTaskBlockingIssue, string>,
  warnings: {
    no_negative_prompt: "未填写反向提示词",
    no_camera_motion: "未填写镜头运动",
    no_seed: "未固定随机种子，运行时会自动冻结一个种子",
    low_resolution: "分辨率较低",
    high_estimated_runtime: "预计运行时间较长",
    same_start_and_end_frame: "起始帧和结束帧相同，将作为提示保留但不会阻止生成"
  } satisfies Record<VideoTaskWarning, string>,
  disabledReasons: {
    notReadyStatus: "请先将视频任务标记为就绪。",
    notReadyReadiness: "任务仍有未满足条件。",
    providerOffline: "ComfyUI 当前不可用。",
    workflowMissing: "请选择视频工作流。",
    workflowUnavailable: "当前工作流不可用，请检查本地 workflow 文件和依赖节点。",
    activeRun: "当前任务已有生成正在执行。"
  }
};

export function videoMissingRequirementText(value: string): string {
  if (value === "provider_offline") return "ComfyUI 当前未连接";
  if (value === "workflow_file_missing") return "本地缺少对应的 workflow JSON 文件";
  if (value === "required_node_types_unavailable") return "无法读取 ComfyUI 节点信息";
  if (value.startsWith("node_type_missing:")) return `ComfyUI 缺少节点：${value.split(":")[1]}`;
  if (value.startsWith("workflow_node_missing:")) return `工作流缺少节点：${value.split(":")[1]}`;
  if (value.startsWith("workflow_input_missing:")) return `工作流缺少输入：${value.split(":")[1]}`;
  return value;
}
