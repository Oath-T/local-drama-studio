export const zhCN = {
  app: {
    subtitle: "本地短剧制作",
    unnamedProject: "未命名项目",
    workbenchFoundation: "项目工作台",
    taskStatusIdle: "任务状态：空闲",
    localMode: "本地开发模式",
    expandSidebar: "展开侧栏",
    collapseSidebar: "折叠侧栏",
    mainNavigation: "主导航"
  },
  nav: {
    projects: "项目",
    characters: "角色库",
    scenes: "场景库",
    shots: "镜头",
    tasks: "生成任务"
  },
  common: {
    loading: "正在加载",
    retry: "重试",
    cancel: "取消",
    save: "保存",
    create: "创建",
    edit: "编辑",
    delete: "删除",
    open: "打开",
    actions: "更多操作",
    backToProjects: "返回项目列表"
  },
  projects: {
    title: "项目",
    description: "管理短剧项目和制作设置",
    newProject: "新建项目",
    editProject: "编辑项目",
    openProject: "打开项目",
    emptyTitle: "当前还没有项目",
    emptyDescription: "创建第一个短剧项目，开始管理角色、场景和镜头。",
    noDescription: "暂无简介",
    coverPlaceholder: "封面占位",
    aspectRatio: "画面比例",
    defaultLanguage: "默认内容语言",
    defaultFps: "默认帧率",
    defaultStyle: "默认视觉风格",
    updatedAt: "最近修改",
    createdAt: "创建时间",
    detailPlaceholder: "项目工作台将在后续 Sprint 中加入角色、场景和镜头管理。",
    notFoundTitle: "项目不存在或已被删除",
    notFoundDescription: "请返回项目列表，确认项目是否仍然存在。",
    deleted: "项目已删除",
    created: "项目已创建",
    updated: "项目设置已更新",
    loadFailed: "项目数据加载失败，请稍后重试。",
    saveFailed: "项目信息保存失败。",
    deleteFailed: "项目删除失败。",
    deleteProject: "删除项目",
    deleteDescription: (name: string) =>
      `确定删除项目“${name}”吗？此操作当前只会删除项目记录，且无法撤销。`
  },
  form: {
    name: "项目名称",
    description: "项目简介",
    aspectRatio: "画面比例",
    defaultStyle: "默认视觉风格",
    defaultLanguage: "默认内容语言",
    defaultFps: "默认帧率",
    namePlaceholder: "请输入项目名称",
    descriptionPlaceholder: "简要描述项目题材、人物关系或制作方向",
    stylePlaceholder: "例如：写实都市短剧、电影级冷色调、古风仙侠",
    creating: "正在创建",
    saving: "正在保存",
    createSubmit: "创建项目",
    saveSubmit: "保存设置",
    errors: {
      nameRequired: "请输入项目名称",
      nameTooLong: "项目名称不能超过 100 个字符",
      descriptionTooLong: "项目简介不能超过 1000 个字符",
      invalidAspectRatio: "请选择有效的画面比例",
      styleTooLong: "默认视觉风格不能超过 200 个字符",
      invalidLanguage: "请选择有效的默认语言",
      invalidFps: "请选择有效的默认帧率"
    }
  },
  options: {
    aspectRatio: {
      "9:16": "9:16：竖屏短剧",
      "16:9": "16:9：横屏视频",
      "1:1": "1:1：方形画面",
      "4:3": "4:3：传统画幅"
    },
    language: {
      "zh-CN": "简体中文",
      "en-US": "English"
    },
    fps: {
      24: "24 FPS",
      25: "25 FPS",
      30: "30 FPS"
    }
  },
  errors: {
    unableToConnect: "无法连接到后端服务。",
    requestFailed: "请求失败，请稍后重试。",
    requestTimeout: "请求超时，请稍后重试。",
    projectNotFound: "项目不存在或已被删除。",
    invalidProjectId: "项目 ID 格式无效。",
    validationFailed: "请检查输入内容。"
  },
  empty: {
    charactersTitle: "角色库尚未实现",
    charactersDescription: "本页会在后续 Sprint 中用于管理人物定妆照、服装和表情参考。",
    scenesTitle: "场景库尚未实现",
    scenesDescription: "本页会在后续 Sprint 中用于管理场景、道具和环境参考。",
    shotsTitle: "镜头系统尚未实现",
    shotsDescription: "本页会在后续 Sprint 中用于组织镜头和参考图片选择。",
    tasksTitle: "生成任务尚未实现",
    tasksDescription: "当前 Sprint 不调用图像模型、视频模型或 ComfyUI。"
  }
} as const;
