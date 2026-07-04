from enum import StrEnum


class KeyframeGenerationRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


ACTIVE_RUN_STATUSES = (
    KeyframeGenerationRunStatus.QUEUED.value,
    KeyframeGenerationRunStatus.RUNNING.value,
)


TERMINAL_RUN_STATUSES = (
    KeyframeGenerationRunStatus.COMPLETED.value,
    KeyframeGenerationRunStatus.FAILED.value,
    KeyframeGenerationRunStatus.CANCELLED.value,
    KeyframeGenerationRunStatus.INTERRUPTED.value,
)


class KeyframeGenerationErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "project_not_found"
    KEYFRAME_TASK_NOT_FOUND = "keyframe_task_not_found"
    PROVIDER_NOT_CONFIGURED = "keyframe_provider_not_configured"
    COMFYUI_UNAVAILABLE = "comfyui_unavailable"
    COMFYUI_TIMEOUT = "comfyui_timeout"
    COMFYUI_INVALID_RESPONSE = "comfyui_invalid_response"
    COMFYUI_SUBMISSION_FAILED = "comfyui_submission_failed"
    COMFYUI_NODE_ERROR = "comfyui_node_error"
    COMFYUI_JOB_NOT_FOUND = "comfyui_job_not_found"
    COMFYUI_EXECUTION_FAILED = "comfyui_execution_failed"
    COMFYUI_OUTPUT_MISSING = "comfyui_output_missing"
    COMFYUI_OUTPUT_DOWNLOAD_FAILED = "comfyui_output_download_failed"
    WORKFLOW_NOT_FOUND = "workflow_not_found"
    WORKFLOW_MANIFEST_INVALID = "workflow_manifest_invalid"
    WORKFLOW_NODE_MISSING = "workflow_node_missing"
    WORKFLOW_INPUT_MISSING = "workflow_input_missing"
    WORKFLOW_MODEL_MISSING = "workflow_model_missing"
    WORKFLOW_OUTPUT_COUNT_UNSUPPORTED = "workflow_output_count_unsupported"
    WORKFLOW_SAMPLER_UNSUPPORTED = "workflow_sampler_unsupported"
    WORKFLOW_SCHEDULER_UNSUPPORTED = "workflow_scheduler_unsupported"
    TASK_NOT_READY = "task_not_ready"
    GENERATION_ALREADY_RUNNING = "generation_already_running"
    GENERATION_RUN_NOT_FOUND = "generation_run_not_found"
    GENERATION_OUTPUT_NOT_FOUND = "generation_output_not_found"
    GENERATION_INTERRUPTED = "generation_interrupted"
    REFERENCE_UPLOAD_FAILED = "reference_upload_failed"
    GENERATED_MEDIA_SAVE_FAILED = "generated_media_save_failed"
    DATABASE_CONFLICT = "database_conflict"


KEYFRAME_GENERATION_ERROR_MESSAGES: dict[str, str] = {
    KeyframeGenerationErrorCode.PROJECT_NOT_FOUND.value: "项目不存在或已被删除。",
    KeyframeGenerationErrorCode.KEYFRAME_TASK_NOT_FOUND.value: "关键帧任务不存在或已被删除。",
    KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED.value: "关键帧生成服务尚未配置。",
    KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE.value: "ComfyUI 未连接，请确认本地服务已启动。",
    KeyframeGenerationErrorCode.COMFYUI_TIMEOUT.value: "ComfyUI 响应超时，请稍后重试。",
    KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE.value: "ComfyUI 返回了无法识别的响应。",
    KeyframeGenerationErrorCode.COMFYUI_SUBMISSION_FAILED.value: "ComfyUI 提交生成任务失败。",
    KeyframeGenerationErrorCode.COMFYUI_NODE_ERROR.value: "ComfyUI 工作流节点校验失败。",
    KeyframeGenerationErrorCode.COMFYUI_JOB_NOT_FOUND.value: "未能确认 ComfyUI 生成任务状态。",
    KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED.value: "ComfyUI 执行过程中失败。",
    KeyframeGenerationErrorCode.COMFYUI_OUTPUT_MISSING.value: "ComfyUI 未返回可保存的图片输出。",
    KeyframeGenerationErrorCode.COMFYUI_OUTPUT_DOWNLOAD_FAILED.value: "生成图片下载失败。",
    KeyframeGenerationErrorCode.WORKFLOW_NOT_FOUND.value: "工作流不存在或未注册。",
    KeyframeGenerationErrorCode.WORKFLOW_MANIFEST_INVALID.value: "工作流配置文件无效。",
    KeyframeGenerationErrorCode.WORKFLOW_NODE_MISSING.value: "工作流缺少必要节点。",
    KeyframeGenerationErrorCode.WORKFLOW_INPUT_MISSING.value: "工作流节点缺少必要输入。",
    KeyframeGenerationErrorCode.WORKFLOW_MODEL_MISSING.value: "工作流依赖的模型尚未配置。",
    KeyframeGenerationErrorCode.WORKFLOW_OUTPUT_COUNT_UNSUPPORTED.value: (
        "当前基础工作流仅支持单次生成一张图片，请将输出数量调整为 1。"
    ),
    KeyframeGenerationErrorCode.WORKFLOW_SAMPLER_UNSUPPORTED.value: "当前工作流不支持该采样器。",
    KeyframeGenerationErrorCode.WORKFLOW_SCHEDULER_UNSUPPORTED.value: "当前工作流不支持该调度器。",
    KeyframeGenerationErrorCode.TASK_NOT_READY.value: "当前关键帧任务尚未准备完成。",
    KeyframeGenerationErrorCode.GENERATION_ALREADY_RUNNING.value: ("当前任务已有生成正在执行。"),
    KeyframeGenerationErrorCode.GENERATION_RUN_NOT_FOUND.value: "生成记录不存在或已被删除。",
    KeyframeGenerationErrorCode.GENERATION_OUTPUT_NOT_FOUND.value: "生成结果不存在或已被删除。",
    KeyframeGenerationErrorCode.GENERATION_INTERRUPTED.value: "生成任务已中断，请重新生成。",
    KeyframeGenerationErrorCode.REFERENCE_UPLOAD_FAILED.value: "参考图上传到生成服务失败。",
    KeyframeGenerationErrorCode.GENERATED_MEDIA_SAVE_FAILED.value: "生成图片保存失败。",
    KeyframeGenerationErrorCode.DATABASE_CONFLICT.value: "数据已被其他操作更新，请刷新后重试。",
}
