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
