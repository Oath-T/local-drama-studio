from dataclasses import dataclass
from enum import StrEnum


class VisionAnalysisTargetType(StrEnum):
    CHARACTER_REFERENCE = "character_reference"
    SCENE_REFERENCE = "scene_reference"


class VisionAnalysisTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VisionAnalysisErrorCode(StrEnum):
    PROVIDER_NOT_CONFIGURED = "vision_provider_not_configured"
    PROVIDER_AUTH_FAILED = "vision_provider_auth_failed"
    PROVIDER_RATE_LIMITED = "vision_provider_rate_limited"
    PROVIDER_TIMEOUT = "vision_provider_timeout"
    PROVIDER_UNAVAILABLE = "vision_provider_unavailable"
    PROVIDER_REFUSED = "vision_provider_refused"
    OUTPUT_INVALID = "vision_output_invalid"
    MEDIA_NOT_FOUND = "media_not_found"
    MEDIA_READ_FAILED = "media_read_failed"
    ANALYSIS_ALREADY_RUNNING = "analysis_already_running"
    ANALYSIS_TASK_NOT_FOUND = "analysis_task_not_found"
    ANALYSIS_INTERRUPTED = "analysis_interrupted"
    ANALYSIS_FAILED = "analysis_failed"
    SUGGESTION_NOT_AVAILABLE = "suggestion_not_available"
    SUGGESTION_VALIDATION_FAILED = "suggestion_validation_failed"


ALLOWED_TASK_TRANSITIONS = {
    VisionAnalysisTaskStatus.PENDING: {
        VisionAnalysisTaskStatus.RUNNING,
        VisionAnalysisTaskStatus.FAILED,
    },
    VisionAnalysisTaskStatus.RUNNING: {
        VisionAnalysisTaskStatus.COMPLETED,
        VisionAnalysisTaskStatus.FAILED,
    },
}


VISION_ERROR_MESSAGES: dict[str, str] = {
    VisionAnalysisErrorCode.PROVIDER_NOT_CONFIGURED.value: (
        "视觉分析服务尚未配置，请先检查本地环境配置。"
    ),
    VisionAnalysisErrorCode.PROVIDER_AUTH_FAILED.value: (
        "视觉分析服务鉴权失败，请检查本地 API Key 配置。"
    ),
    VisionAnalysisErrorCode.PROVIDER_RATE_LIMITED.value: ("视觉分析服务请求过于频繁，请稍后重试。"),
    VisionAnalysisErrorCode.PROVIDER_TIMEOUT.value: "视觉分析请求超时，请稍后重试。",
    VisionAnalysisErrorCode.PROVIDER_UNAVAILABLE.value: ("视觉分析服务暂时不可用，请稍后重试。"),
    VisionAnalysisErrorCode.PROVIDER_REFUSED.value: (
        "视觉分析服务拒绝处理这张图片，请更换图片或手动填写元数据。"
    ),
    VisionAnalysisErrorCode.OUTPUT_INVALID.value: "视觉分析返回结构无效，请稍后重试。",
    VisionAnalysisErrorCode.MEDIA_NOT_FOUND.value: "参考图文件不存在或已被删除。",
    VisionAnalysisErrorCode.MEDIA_READ_FAILED.value: (
        "参考图文件读取失败，请检查文件是否仍在本地存储中。"
    ),
    VisionAnalysisErrorCode.ANALYSIS_ALREADY_RUNNING.value: ("这张参考图已有分析任务正在运行。"),
    VisionAnalysisErrorCode.ANALYSIS_TASK_NOT_FOUND.value: "分析任务不存在或已被删除。",
    VisionAnalysisErrorCode.ANALYSIS_INTERRUPTED.value: (
        "上一次分析因服务重启中断，请重新发起分析。"
    ),
    VisionAnalysisErrorCode.ANALYSIS_FAILED.value: "视觉分析失败，请稍后重试。",
    VisionAnalysisErrorCode.SUGGESTION_NOT_AVAILABLE.value: "当前参考图没有可审核的分析建议。",
    VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED.value: (
        "分析建议校验失败，请重新分析或手动填写。"
    ),
}


@dataclass(frozen=True)
class VisionProviderRuntimeError(Exception):
    code: VisionAnalysisErrorCode
    message: str
    retryable: bool = False


def can_transition(
    current: VisionAnalysisTaskStatus,
    target: VisionAnalysisTaskStatus,
) -> bool:
    return target in ALLOWED_TASK_TRANSITIONS.get(current, set())
