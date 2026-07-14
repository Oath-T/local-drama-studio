import type {
  KeyframeTaskBlockingIssue,
  KeyframeTaskPurpose,
  KeyframeTaskReadinessStatus,
  KeyframeTaskStatus,
  KeyframeTaskWarningIssue
} from "./types";

export const keyframeTaskCopy = {
  tab: "关键帧任务",
  title: "关键帧生成任务",
  description: "整理镜头快照、提示词、参数和任务参考图；准备完成后可提交到本地 ComfyUI 生成关键帧。",
  create: "新建任务",
  creating: "正在创建",
  edit: "编辑任务",
  save: "保存任务",
  saving: "正在保存",
  duplicate: "复制",
  delete: "删除任务",
  deleted: "任务已删除",
  duplicated: "任务已复制",
  created: "任务已创建",
  saved: "任务已保存",
  markedReady: "任务已标记为准备完成",
  markedDraft: "任务已退回草稿",
  markReady: "标记准备完成",
  markDraft: "退回草稿",
  loadFailed: "关键帧任务加载失败，请稍后重试。",
  saveFailed: "关键帧任务保存失败。",
  deleteFailed: "关键帧任务删除失败。",
  referenceSaveFailed: "任务参考图保存失败。",
  referenceDeleteFailed: "任务参考图移除失败。",
  emptyTitle: "当前镜头还没有关键帧任务",
  emptyDescription: "创建任务后，可以检查镜头快照、提示词、生成参数和参考图是否准备完整。",
  noGeneration: "进入任务编辑后，可以查看 ComfyUI 状态并手动开始生成。",
  deleteDescription: (name: string) =>
    `确定删除关键帧任务“${name}”吗？这只会删除任务和任务参考绑定，不会删除镜头、资产库或媒体文件。`,
  sourceDeleted: "源参考已删除",
  noReferences: "当前任务还没有参考图。",
  noShotReferences: "当前镜头还没有可加入任务的参考图。",
  addReference: "加入任务",
  addReferenceTitle: "从当前镜头参考图加入",
  currentShotReferencesOnly: "只能从当前镜头已绑定的参考图中选择，不会直接读取资产库。",
  readiness: {
    incomplete: "未完成",
    ready: "准备完成"
  } satisfies Record<KeyframeTaskReadinessStatus, string>,
  status: {
    draft: "草稿",
    ready: "准备完成"
  } satisfies Record<KeyframeTaskStatus, string>,
  purpose: {
    first_frame: "首帧",
    end_frame: "尾帧",
    concept: "概念图",
    reference: "参考图"
  } satisfies Record<KeyframeTaskPurpose, string>,
  fields: {
    name: "任务名称",
    promptZh: "中文提示词",
    promptEn: "英文提示词",
    negativePrompt: "负面提示词",
    aspectRatio: "画幅比例",
    width: "宽度",
    height: "高度",
    seed: "随机种子",
    steps: "推理步数",
    guidance: "引导强度",
    sampler: "采样器",
    scheduler: "调度器",
    provider: "模型提供方",
    model: "模型名称",
    modelVersion: "模型版本",
    outputCount: "输出数量",
    purpose: "用途",
    reference: "参考图"
  },
  hints: {
    seed: "留空表示随机；0 是有效的固定种子。",
    dimensions: "宽高必须在 256 到 4096 之间，且为 8 的倍数。画幅不匹配会阻止准备完成，但不会阻止保存。",
    snapshot: "任务保存的是创建时的镜头快照；镜头后续变化会显示 warning，需要手动检查。",
    provider: "模型信息只是配置占位，本轮不会调用任何模型。"
  },
  blockingIssues: {
    missing_name: "缺少任务名称",
    no_prompt: "缺少提示词",
    invalid_dimensions: "尺寸无效",
    aspect_ratio_mismatch: "宽高与画幅比例不匹配",
    invalid_steps: "推理步数无效",
    invalid_guidance: "引导强度无效",
    invalid_output_count: "输出数量无效",
    missing_primary_character_reference: "缺少主要角色参考图",
    missing_scene_reference: "缺少匹配场景状态的场景参考图",
    unavailable_media: "存在不可用媒体"
  } satisfies Record<KeyframeTaskBlockingIssue, string>,
  warnings: {
    no_english_prompt: "未填写英文提示词",
    no_negative_prompt: "未填写负面提示词",
    no_model_selected: "未选择模型",
    shot_changed_since_snapshot: "镜头已在任务创建后发生变化",
    no_identity_reference: "未包含身份参考",
    no_spatial_reference: "未包含空间结构参考",
    no_seed: "未固定随机种子",
    missing_secondary_character_reference: "部分次要角色缺少参考图"
  } satisfies Record<KeyframeTaskWarningIssue, string>
};
