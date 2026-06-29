export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const requestTimeoutMs = 10000;

const errorCodeMessages: Record<string, string> = {
  PROJECT_NOT_FOUND: "项目不存在或已被删除。",
  CHARACTER_NOT_FOUND: "角色不存在或已被删除。",
  CHARACTER_LOOK_NOT_FOUND: "造型不存在或已被删除。",
  CHARACTER_REFERENCE_NOT_FOUND: "参考图不存在或已被删除。",
  SCENE_NOT_FOUND: "场景不存在或已被删除。",
  SCENE_STATE_NOT_FOUND: "场景状态不存在或已被删除。",
  SCENE_REFERENCE_NOT_FOUND: "场景参考图不存在或已被删除。",
  SHOT_NOT_FOUND: "镜头不存在或已被删除。",
  SHOT_NAME_REQUIRED: "请输入镜头名称。",
  SHOT_DURATION_SECONDS_POSITIVE: "预计时长必须大于 0 秒。",
  SHOT_CHARACTER_NOT_FOUND: "镜头角色不存在或已被删除。",
  SHOT_REFERENCE_NOT_FOUND: "镜头参考图绑定不存在或已被删除。",
  SHOT_CHARACTER_ALREADY_BOUND: "该角色已经绑定到当前镜头。",
  SHOT_REFERENCE_ALREADY_BOUND: "相同用途的参考图已经绑定。",
  SHOT_SCENE_REQUIRED: "请先为镜头选择场景。",
  SHOT_SCENE_STATE_REQUIRED: "请先为镜头选择场景状态。",
  INVALID_SHOT_ID: "镜头 ID 格式无效。",
  INVALID_SHOT_CHARACTER_ID: "镜头角色 ID 格式无效。",
  INVALID_SHOT_REFERENCE_ID: "镜头参考图 ID 格式无效。",
  SCENE_NAME_REQUIRED: "请输入场景名称。",
  SCENE_STATE_NAME_REQUIRED: "请输入场景状态名称。",
  CUSTOM_WEATHER_REQUIRED: "选择自定义天气时，请填写天气说明。",
  CUSTOM_LIGHTING_REQUIRED: "选择自定义灯光时，请填写灯光说明。",
  CUSTOM_CAMERA_POSITION_REQUIRED: "选择自定义机位时，请填写机位说明。",
  CUSTOM_VIEW_DIRECTION_REQUIRED: "选择自定义朝向时，请填写朝向说明。",
  CUSTOM_COMPOSITION_REQUIRED: "选择自定义构图时，请填写构图说明。",
  LAST_SCENE_STATE_DELETE_FORBIDDEN: "不能删除场景的最后一个状态。",
  CHARACTER_NAME_REQUIRED: "请输入角色名称。",
  CHARACTER_LOOK_NAME_REQUIRED: "请输入造型名称。",
  LAST_LOOK_DELETE_FORBIDDEN: "不能删除角色的最后一套造型。",
  INVALID_PROJECT_ID: "项目 ID 格式无效。",
  INVALID_CHARACTER_ID: "角色 ID 格式无效。",
  INVALID_LOOK_ID: "造型 ID 格式无效。",
  INVALID_REFERENCE_ID: "参考图 ID 格式无效。",
  INVALID_SCENE_ID: "场景 ID 格式无效。",
  INVALID_SCENE_STATE_ID: "场景状态 ID 格式无效。",
  IMAGE_EXTENSION_NOT_ALLOWED: "仅支持 JPG、PNG 和 WEBP 图片。",
  IMAGE_TOO_LARGE: "图片文件不能超过限制大小。",
  IMAGE_INVALID: "图片文件已损坏或无法识别。",
  FILE_NOT_FOUND: "媒体文件不存在或已被删除。"
};

Object.assign(errorCodeMessages, {
  vision_provider_not_configured: "视觉分析服务尚未配置，请先检查本地环境配置。",
  vision_provider_auth_failed: "视觉分析服务鉴权失败，请检查本地 API Key 配置。",
  vision_provider_rate_limited: "视觉分析服务请求过于频繁，请稍后重试。",
  vision_provider_timeout: "视觉分析请求超时，请稍后重试。",
  vision_provider_unavailable: "视觉分析服务暂时不可用，请稍后重试。",
  vision_provider_refused: "视觉分析服务拒绝处理这张图片，请更换图片或手动填写元数据。",
  vision_output_invalid: "视觉分析返回结构无效，请稍后重试。",
  media_not_found: "参考图文件不存在或已被删除。",
  media_read_failed: "参考图文件读取失败，请检查文件是否仍在本地存储中。",
  analysis_already_running: "这张参考图已有分析任务正在运行。",
  analysis_task_not_found: "分析任务不存在或已被删除。",
  analysis_interrupted: "上一次分析因服务重启中断，请重新发起分析。",
  analysis_failed: "视觉分析失败，请稍后重试。",
  suggestion_not_available: "当前参考图没有可审核的分析建议。",
  suggestion_validation_failed: "分析建议校验失败，请重新分析或手动填写。"
});

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

interface ErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}

async function parseError(response: Response): Promise<ApiClientError> {
  try {
    const payload = (await response.json()) as ErrorPayload;
    const code = payload.error?.code;
    return new ApiClientError(
      (code ? errorCodeMessages[code] : undefined) ??
        payload.error?.message ??
        `请求失败，状态码 ${response.status}。`,
      response.status,
      code
    );
  } catch {
    return new ApiClientError(`请求失败，状态码 ${response.status}。`, response.status);
  }
}

export async function apiRequest<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);
  let response: Response;

  try {
    const isFormData = init.body instanceof FormData;
    response = await fetch(buildUrl(path), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body && !isFormData ? { "Content-Type": "application/json" } : {}),
        ...init.headers
      },
      signal: controller.signal
    });
  } catch (error) {
    const message =
      error instanceof DOMException && error.name === "AbortError"
        ? "请求超时，请稍后重试。"
        : "无法连接到后端服务。";
    throw new ApiClientError(message);
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export async function apiGet<TResponse>(path: string): Promise<TResponse> {
  return apiRequest<TResponse>(path, { method: "GET" });
}

export async function apiPost<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, { method: "POST", body: JSON.stringify(body) });
}

export async function apiPatch<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export async function apiDelete(path: string): Promise<void> {
  await apiRequest<void>(path, { method: "DELETE" });
}

export async function apiPostForm<TResponse>(
  path: string,
  body: FormData
): Promise<TResponse> {
  return apiRequest<TResponse>(path, { method: "POST", body });
}
