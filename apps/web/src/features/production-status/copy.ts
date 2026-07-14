import type {
  AssetStepStatus,
  DirectorPromptStatus,
  FrameStepStatus,
  ProductionAction,
  ProductionOverallStatus,
  VideoStepStatus
} from "./types";

export const productionStatusCopy = {
  title: "生产流程",
  boardTitle: "生产看板",
  boardDescription: "按镜头查看资产、Prompt、首帧、尾帧、视频和最终采用状态。这里只读汇总，不会触发生成。",
  loadFailed: "生产状态加载失败，请稍后重试。",
  emptyTitle: "暂无镜头生产状态",
  emptyDescription: "创建镜头后，这里会显示每个镜头的生产进度。",
  noBlockers: "当前没有阻断项。",
  continuityTitle: "连续性候选",
  continuityDescription: "可参考上一镜头已采用的视频或尾帧输出，但不会自动填入。",
  inheritedFramesConfirm:
    "检测到当前镜头已有采用的首帧 / 尾帧输出，是否填入新建的视频任务？\n不会标记就绪，也不会开始生成。",
  partialInheritedFramesConfirm:
    "检测到当前镜头已有部分采用的关键帧输出，是否填入新建的视频任务？\n缺少的输入仍需手动选择。",
  videoTaskCreatedWithFrames: "已创建视频任务草稿，并填入已采用的首尾帧，请检查后手动保存或标记就绪。",
  videoTaskFrameFillFailed: "视频任务已创建，但首尾帧填入失败，请在视频任务中手动选择。",
  steps: {
    assets: "资产准备",
    director_prompt: "导演 Prompt",
    first_frame: "首帧",
    end_frame: "尾帧",
    video: "视频",
    final_adoption: "最终采用"
  },
  overall: {
    blocked: "有阻断",
    in_progress: "进行中",
    ready_for_video: "可进入视频",
    completed: "已完成"
  } satisfies Record<ProductionOverallStatus, string>,
  assetStatus: {
    complete: "完整",
    warning: "需检查",
    missing: "缺失"
  } satisfies Record<AssetStepStatus, string>,
  directorStatus: {
    not_created: "未生成",
    available: "可生成"
  } satisfies Record<DirectorPromptStatus, string>,
  frameStatus: {
    not_created: "未创建",
    draft: "草稿",
    ready: "就绪",
    running: "生成中",
    completed: "有输出",
    adopted: "已采用"
  } satisfies Record<FrameStepStatus, string>,
  videoStatus: {
    not_created: "未创建",
    missing_inputs: "缺少输入",
    draft: "草稿",
    ready: "就绪",
    running: "生成中",
    completed: "有输出",
    adopted: "已采用"
  } satisfies Record<VideoStepStatus, string>,
  action: {
    bind_character: "添加镜头角色",
    bind_scene: "选择场景和状态",
    create_director_prompt: "生成导演 Prompt",
    create_first_frame_task: "创建首帧任务",
    create_end_frame_task: "创建尾帧任务",
    select_first_frame: "采用首帧输出",
    select_end_frame: "采用尾帧输出",
    create_video_task: "创建视频任务",
    fill_video_inputs: "填入视频首尾帧",
    review_final_output: "检查并采用最终视频"
  } satisfies Record<ProductionAction, string>,
  filters: {
    all: "全部",
    blocked: "有阻断",
    in_progress: "进行中",
    ready_for_video: "可进入视频",
    completed: "已完成"
  },
  openShot: "打开镜头",
  openTasks: "查看任务",
  createVideoTask: "用已采用首尾帧创建视频任务",
  startFrameSelected: "首帧已采用",
  endFrameSelected: "尾帧已采用",
  startFrameMissing: "首帧未采用",
  endFrameMissing: "尾帧未采用"
};
