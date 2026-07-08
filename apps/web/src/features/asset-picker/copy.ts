import type { PickerAssetType } from "./types";

export const assetPickerCopy = {
  searchPlaceholder: "搜索资产",
  loading: "正在加载可选资产...",
  loadFailed: "资产列表加载失败，请稍后重试。",
  retry: "重新加载",
  emptyTitle: "当前没有可选资产",
  emptyDescription: {
    character: "请先在角色库创建人物并补充基础资产。",
    scene: "请先在场景库创建场景并补充基础资产。",
    frame_image: "当前镜头还没有可作为视频首尾帧的图片。",
    character_look: "当前人物还没有可用造型。",
    scene_state: "当前场景还没有可用状态。",
    reference_image: "当前镜头上下文还没有可用参考图。"
  } satisfies Record<PickerAssetType, string>,
  selected: "已选择",
  selectedBound: "已绑定",
  select: "选择",
  cancel: "取消",
  confirm: "确认选择",
  noPreview: "未选择资产",
  disabledSelected: "该资产已在当前镜头中使用。",
  disabledTaskReference: "该参考图已经加入当前关键帧任务，或不能直接加入任务。",
  chooseCharacter: "从资产库选择人物",
  chooseScene: "从资产库选择场景",
  chooseCharacterLook: "更换人物造型",
  chooseSceneState: "选择场景状态",
  chooseReferenceImage: "从资产选择参考图",
  chooseTaskReference: "从镜头资产选择参考图",
  chooseStartFrame: "从资产选择首帧",
  chooseEndFrame: "从资产选择尾帧",
  referenceDescription: "这里选择的是当前镜头上下文中的人物或场景参考图。",
  taskReferenceDescription: "关键帧任务本轮只允许加入当前镜头已绑定的参考图。",
  frameDescription:
    "这里选择的是视频首尾帧输入。人物/场景资产不会直接进入当前 Wan2.2 workflow。"
};
