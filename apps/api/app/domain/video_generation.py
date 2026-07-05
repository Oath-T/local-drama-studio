from enum import StrEnum


class VideoGenerationTaskStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class VideoGenerationRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


ACTIVE_VIDEO_RUN_STATUSES = (
    VideoGenerationRunStatus.QUEUED.value,
    VideoGenerationRunStatus.RUNNING.value,
)


class VideoInputRole(StrEnum):
    START_FRAME = "start_frame"
    END_FRAME = "end_frame"


VIDEO_INPUT_ROLE_ORDER = {
    VideoInputRole.START_FRAME.value: 1,
    VideoInputRole.END_FRAME.value: 2,
}


class VideoWorkflowMode(StrEnum):
    SINGLE_IMAGE_TO_VIDEO = "single_image_to_video"
    FIRST_LAST_FRAME_TO_VIDEO = "first_last_frame_to_video"


class VideoTaskReadinessStatus(StrEnum):
    READY = "ready"
    INCOMPLETE = "incomplete"


class VideoTaskBlockingIssue(StrEnum):
    MISSING_NAME = "missing_name"
    MISSING_INPUT_IMAGE = "missing_input_image"
    MISSING_START_FRAME = "missing_start_frame"
    MISSING_END_FRAME = "missing_end_frame"
    INPUT_IMAGE_UNAVAILABLE = "input_image_unavailable"
    START_FRAME_UNAVAILABLE = "start_frame_unavailable"
    END_FRAME_UNAVAILABLE = "end_frame_unavailable"
    INPUT_IMAGE_NOT_IMAGE = "input_image_not_image"
    START_FRAME_NOT_IMAGE = "start_frame_not_image"
    END_FRAME_NOT_IMAGE = "end_frame_not_image"
    MISSING_PROMPT = "missing_prompt"
    INVALID_DURATION = "invalid_duration"
    INVALID_FPS = "invalid_fps"
    INVALID_DIMENSIONS = "invalid_dimensions"
    INVALID_SEED = "invalid_seed"
    WORKFLOW_NOT_SELECTED = "workflow_not_selected"
    WORKFLOW_UNAVAILABLE = "workflow_unavailable"
    WORKFLOW_REQUIRES_END_FRAME = "workflow_requires_end_frame"


class VideoTaskWarning(StrEnum):
    NO_NEGATIVE_PROMPT = "no_negative_prompt"
    NO_CAMERA_MOTION = "no_camera_motion"
    NO_SEED = "no_seed"
    LOW_RESOLUTION = "low_resolution"
    HIGH_ESTIMATED_RUNTIME = "high_estimated_runtime"
    SAME_START_AND_END_FRAME = "same_start_and_end_frame"


class VideoGenerationErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "project_not_found"
    SHOT_NOT_FOUND = "shot_not_found"
    VIDEO_TASK_NOT_FOUND = "video_task_not_found"
    VIDEO_TASK_NOT_READY = "video_task_not_ready"
    VIDEO_INPUT_IMAGE_MISSING = "video_input_image_missing"
    VIDEO_INPUT_IMAGE_UNAVAILABLE = "video_input_image_unavailable"
    VIDEO_INPUT_IMAGE_INVALID = "video_input_image_invalid"
    VIDEO_INPUT_ROLE_INVALID = "video_input_role_invalid"
    VIDEO_INPUT_ROLE_DUPLICATE = "video_input_role_duplicate"
    VIDEO_WORKFLOW_NOT_SELECTED = "video_workflow_not_selected"
    VIDEO_WORKFLOW_UNAVAILABLE = "video_workflow_unavailable"
    VIDEO_GENERATION_ALREADY_RUNNING = "video_generation_already_running"
    VIDEO_PROVIDER_NOT_CONFIGURED = "video_provider_not_configured"
    VIDEO_COMFYUI_UNAVAILABLE = "video_comfyui_unavailable"
    VIDEO_COMFYUI_TIMEOUT = "video_comfyui_timeout"
    VIDEO_COMFYUI_INVALID_RESPONSE = "video_comfyui_invalid_response"
    VIDEO_COMFYUI_SUBMISSION_FAILED = "video_comfyui_submission_failed"
    VIDEO_COMFYUI_NODE_ERROR = "video_comfyui_node_error"
    VIDEO_COMFYUI_EXECUTION_FAILED = "video_comfyui_execution_failed"
    VIDEO_OUTPUT_MISSING = "video_output_missing"
    VIDEO_OUTPUT_DOWNLOAD_FAILED = "video_output_download_failed"
    VIDEO_OUTPUT_SAVE_FAILED = "video_output_save_failed"
    VIDEO_REFERENCE_UPLOAD_FAILED = "video_reference_upload_failed"
    VIDEO_RUN_NOT_FOUND = "video_run_not_found"
    VIDEO_GENERATION_INTERRUPTED = "video_generation_interrupted"
    VIDEO_OUTPUT_NOT_FOUND = "video_output_not_found"
    DATABASE_CONFLICT = "database_conflict"
    WORKFLOW_UNAVAILABLE = "video_workflow_unavailable"
    PROVIDER_NOT_CONFIGURED = "video_provider_not_configured"
    COMFYUI_UNAVAILABLE = "video_comfyui_unavailable"
    COMFYUI_TIMEOUT = "video_comfyui_timeout"
    COMFYUI_INVALID_RESPONSE = "video_comfyui_invalid_response"
    COMFYUI_SUBMISSION_FAILED = "video_comfyui_submission_failed"
    COMFYUI_NODE_ERROR = "video_comfyui_node_error"
    COMFYUI_EXECUTION_FAILED = "video_comfyui_execution_failed"
    OUTPUT_MISSING = "video_output_missing"
    OUTPUT_DOWNLOAD_FAILED = "video_output_download_failed"
    OUTPUT_SAVE_FAILED = "video_output_save_failed"
    REFERENCE_UPLOAD_FAILED = "video_reference_upload_failed"


VIDEO_GENERATION_ERROR_MESSAGES: dict[str, str] = {
    VideoGenerationErrorCode.PROJECT_NOT_FOUND.value: "项目不存在或已被删除。",
    VideoGenerationErrorCode.SHOT_NOT_FOUND.value: "镜头不存在或已被删除。",
    VideoGenerationErrorCode.VIDEO_TASK_NOT_FOUND.value: "视频生成任务不存在或已被删除。",
    VideoGenerationErrorCode.VIDEO_TASK_NOT_READY.value: "当前视频生成任务尚未准备完成。",
    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_MISSING.value: "请先选择起始图。",
    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE.value: "起始图不存在或已被删除。",
    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_INVALID.value: "起始图必须是当前项目内的图片媒体。",
    VideoGenerationErrorCode.VIDEO_WORKFLOW_NOT_SELECTED.value: "请先选择视频工作流。",
    VideoGenerationErrorCode.VIDEO_WORKFLOW_UNAVAILABLE.value: "视频工作流当前不可用。",
    VideoGenerationErrorCode.VIDEO_GENERATION_ALREADY_RUNNING.value: (
        "当前任务已有视频生成正在执行。"
    ),
    VideoGenerationErrorCode.VIDEO_PROVIDER_NOT_CONFIGURED.value: "视频生成服务尚未配置。",
    VideoGenerationErrorCode.VIDEO_COMFYUI_UNAVAILABLE.value: (
        "ComfyUI 未连接，请确认本地服务已启动。"
    ),
    VideoGenerationErrorCode.VIDEO_COMFYUI_TIMEOUT.value: "ComfyUI 响应超时，请稍后重试。",
    VideoGenerationErrorCode.VIDEO_COMFYUI_INVALID_RESPONSE.value: "ComfyUI 返回了无法识别的响应。",
    VideoGenerationErrorCode.VIDEO_COMFYUI_SUBMISSION_FAILED.value: (
        "ComfyUI 提交视频生成任务失败。"
    ),
    VideoGenerationErrorCode.VIDEO_COMFYUI_NODE_ERROR.value: "ComfyUI 视频工作流节点校验失败。",
    VideoGenerationErrorCode.VIDEO_COMFYUI_EXECUTION_FAILED.value: "ComfyUI 视频执行过程中失败。",
    VideoGenerationErrorCode.VIDEO_OUTPUT_MISSING.value: "ComfyUI 未返回可保存的视频输出。",
    VideoGenerationErrorCode.VIDEO_OUTPUT_DOWNLOAD_FAILED.value: "视频输出下载失败。",
    VideoGenerationErrorCode.VIDEO_OUTPUT_SAVE_FAILED.value: "视频输出保存失败。",
    VideoGenerationErrorCode.VIDEO_REFERENCE_UPLOAD_FAILED.value: "起始图上传到 ComfyUI 失败。",
    VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND.value: "视频生成记录不存在或已被删除。",
    VideoGenerationErrorCode.VIDEO_GENERATION_INTERRUPTED.value: "视频生成任务已中断，请重新生成。",
    VideoGenerationErrorCode.VIDEO_OUTPUT_NOT_FOUND.value: "视频生成结果不存在或已被删除。",
    VideoGenerationErrorCode.DATABASE_CONFLICT.value: "数据已被其他操作更新，请刷新后重试。",
}

VIDEO_GENERATION_ERROR_MESSAGES[VideoGenerationErrorCode.VIDEO_INPUT_ROLE_INVALID.value] = (
    "视频输入类型不可用。"
)
VIDEO_GENERATION_ERROR_MESSAGES[VideoGenerationErrorCode.VIDEO_INPUT_ROLE_DUPLICATE.value] = (
    "视频输入类型重复。"
)
