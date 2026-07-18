import type { CanvasEdgeType, CanvasNodeType } from "./types";

export const projectCanvasCopy = {
  title: "创作画布",
  workflow: "工作流",
  storyboard: "故事板",
  saved: "已保存",
  saving: "保存中",
  unsaved: "尚未保存",
  saveFailed: "保存失败，点击重试",
  conflict: "数据已在其他页面更新，请重新加载或覆盖。",
  emptyTitle: "从这里开始创作",
  emptyDescription: "把角色、场景、镜头和输出放到画布上，先搭出这个项目的创作关系。",
  addExisting: "将项目现有内容添加到画布",
  addNode: "添加节点",
  autoLayout: "自动整理",
  fitView: "适配视图",
  undo: "撤销",
  redo: "重做",
  assistantTitle: "项目助手",
  assistantSoon: "项目助手即将支持计划建议和确认执行。本轮先提供只读项目摘要。",
  openShotWorkspace: "打开镜头创作工作台",
  openDetail: "打开详情",
  deleteNode: "删除节点",
  duplicateNode: "复制节点",
  bringToFront: "置于顶层",
  collapse: "收起 / 展开",
  nodeType: {
    text: "文本",
    character: "角色",
    scene: "场景",
    shot: "镜头",
    image: "图片",
    video: "视频",
    export: "导出"
  } satisfies Record<CanvasNodeType, string>,
  edgeType: {
    shot_reference: "设为镜头参考图",
    uses_character: "使用角色",
    uses_scene: "使用场景",
    identity_reference: "身份参考",
    look_reference: "造型参考",
    scene_reference: "场景参考",
    pose_reference: "姿态参考",
    start_frame: "首帧",
    end_frame: "尾帧",
    continuity_from: "连续自",
    generated_from: "生成自",
    included_in_export: "加入导出"
  } satisfies Record<CanvasEdgeType, string>
};

export const canvasNodeTypes: CanvasNodeType[] = [
  "text",
  "character",
  "scene",
  "shot",
  "image",
  "video",
  "export"
];
