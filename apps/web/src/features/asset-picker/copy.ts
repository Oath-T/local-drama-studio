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
    frame_image: "当前镜头还没有可作为视频首尾帧的图片。"
  } satisfies Record<PickerAssetType, string>,
  selected: "已选择",
  selectedBound: "已绑定",
  select: "选择",
  cancel: "取消",
  confirm: "确认选择",
  noPreview: "未选择资产",
  disabledSelected: "该资产已在当前镜头中使用。",
  chooseCharacter: "从资产库选择人物",
  chooseScene: "从资产库选择场景",
  chooseStartFrame: "从资产选择首帧",
  chooseEndFrame: "从资产选择尾帧",
  frameDescription:
    "这里选择的是视频首尾帧输入。人物/场景资产不会直接进入当前 Wan2.2 workflow。"
};
