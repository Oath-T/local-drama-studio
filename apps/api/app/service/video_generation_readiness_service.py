from datetime import UTC, datetime

from app.api.schemas.video_generation import VideoTaskReadinessResponse
from app.domain.media_asset import MediaType
from app.domain.video_generation import (
    VideoInputRole,
    VideoTaskBlockingIssue,
    VideoTaskReadinessStatus,
    VideoTaskWarning,
    VideoWorkflowMode,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.video_generation import VideoGenerationTaskRecord
from app.service.media_storage_service import MediaStorageService


class VideoGenerationReadinessService:
    def __init__(self, storage_service: MediaStorageService | None = None) -> None:
        self.storage_service = storage_service or MediaStorageService()

    def calculate(
        self,
        task: VideoGenerationTaskRecord,
        input_media_asset: MediaAssetRecord | None = None,
        *,
        workflow_available: bool,
        input_media_asset_ids_by_role: dict[VideoInputRole, str | None] | None = None,
        input_media_assets_by_role: dict[VideoInputRole, MediaAssetRecord | None] | None = None,
        required_input_roles: list[VideoInputRole] | None = None,
        workflow_mode: VideoWorkflowMode = VideoWorkflowMode.SINGLE_IMAGE_TO_VIDEO,
    ) -> VideoTaskReadinessResponse:
        blocking: set[VideoTaskBlockingIssue] = set()
        warnings: set[VideoTaskWarning] = set()
        ids_by_role = input_media_asset_ids_by_role or {}
        assets_by_role = input_media_assets_by_role or {}
        required_roles = required_input_roles or [VideoInputRole.START_FRAME]
        if not self._has_text(task.name):
            blocking.add(VideoTaskBlockingIssue.MISSING_NAME)
        if ids_by_role:
            self._validate_role_input(
                VideoInputRole.START_FRAME,
                ids_by_role,
                assets_by_role,
                blocking,
            )
            if VideoInputRole.END_FRAME in required_roles:
                self._validate_role_input(
                    VideoInputRole.END_FRAME,
                    ids_by_role,
                    assets_by_role,
                    blocking,
                )
            if (
                workflow_mode == VideoWorkflowMode.FIRST_LAST_FRAME_TO_VIDEO
                and VideoInputRole.END_FRAME not in required_roles
            ):
                blocking.add(VideoTaskBlockingIssue.WORKFLOW_REQUIRES_END_FRAME)
            start_id = ids_by_role.get(VideoInputRole.START_FRAME)
            end_id = ids_by_role.get(VideoInputRole.END_FRAME)
            if start_id and end_id and start_id == end_id:
                warnings.add(VideoTaskWarning.SAME_START_AND_END_FRAME)
        elif not task.input_media_asset_id:
            blocking.add(VideoTaskBlockingIssue.MISSING_START_FRAME)
        elif input_media_asset is None:
            blocking.add(VideoTaskBlockingIssue.START_FRAME_UNAVAILABLE)
        elif input_media_asset.media_type != MediaType.IMAGE.value:
            blocking.add(VideoTaskBlockingIssue.START_FRAME_NOT_IMAGE)
        else:
            try:
                self.storage_service.resolve_relative_path(
                    input_media_asset.relative_path,
                    must_exist=True,
                )
            except Exception:
                blocking.add(VideoTaskBlockingIssue.START_FRAME_UNAVAILABLE)
        if not self._has_text(task.prompt):
            blocking.add(VideoTaskBlockingIssue.MISSING_PROMPT)
        if not task.duration_seconds or task.duration_seconds <= 0:
            blocking.add(VideoTaskBlockingIssue.INVALID_DURATION)
        if not task.fps or task.fps <= 0:
            blocking.add(VideoTaskBlockingIssue.INVALID_FPS)
        if not _valid_dimension(task.width) or not _valid_dimension(task.height):
            blocking.add(VideoTaskBlockingIssue.INVALID_DIMENSIONS)
        if task.seed is not None and task.seed < 0:
            blocking.add(VideoTaskBlockingIssue.INVALID_SEED)
        if not self._has_text(task.workflow_id):
            blocking.add(VideoTaskBlockingIssue.WORKFLOW_NOT_SELECTED)
        elif not workflow_available:
            blocking.add(VideoTaskBlockingIssue.WORKFLOW_UNAVAILABLE)

        if not self._has_text(task.negative_prompt):
            warnings.add(VideoTaskWarning.NO_NEGATIVE_PROMPT)
        if not self._has_text(task.camera_motion):
            warnings.add(VideoTaskWarning.NO_CAMERA_MOTION)
        if task.seed is None:
            warnings.add(VideoTaskWarning.NO_SEED)
        if task.width < 512 or task.height < 512:
            warnings.add(VideoTaskWarning.LOW_RESOLUTION)
        if task.duration_seconds >= 8:
            warnings.add(VideoTaskWarning.HIGH_ESTIMATED_RUNTIME)

        ordered_blocking = [issue for issue in BLOCKING_ORDER if issue in blocking]
        ordered_warnings = [issue for issue in WARNING_ORDER if issue in warnings]
        return VideoTaskReadinessResponse(
            readiness_status=(
                VideoTaskReadinessStatus.READY
                if not ordered_blocking
                else VideoTaskReadinessStatus.INCOMPLETE
            ),
            blocking_issues=ordered_blocking,
            warnings=ordered_warnings,
        )

    def _validate_role_input(
        self,
        role: VideoInputRole,
        ids_by_role: dict[VideoInputRole, str | None],
        assets_by_role: dict[VideoInputRole, MediaAssetRecord | None],
        blocking: set[VideoTaskBlockingIssue],
    ) -> None:
        media_asset_id = ids_by_role.get(role)
        if not media_asset_id:
            blocking.add(_missing_issue(role))
            return
        media_asset = assets_by_role.get(role)
        if media_asset is None:
            blocking.add(_unavailable_issue(role))
            return
        if media_asset.media_type != MediaType.IMAGE.value:
            blocking.add(_not_image_issue(role))
            return
        try:
            self.storage_service.resolve_relative_path(
                media_asset.relative_path,
                must_exist=True,
            )
        except Exception:
            blocking.add(_unavailable_issue(role))

    @staticmethod
    def _has_text(value: str | None) -> bool:
        return bool(value and value.strip())


BLOCKING_ORDER = [
    VideoTaskBlockingIssue.MISSING_NAME,
    VideoTaskBlockingIssue.MISSING_START_FRAME,
    VideoTaskBlockingIssue.MISSING_END_FRAME,
    VideoTaskBlockingIssue.MISSING_INPUT_IMAGE,
    VideoTaskBlockingIssue.START_FRAME_UNAVAILABLE,
    VideoTaskBlockingIssue.END_FRAME_UNAVAILABLE,
    VideoTaskBlockingIssue.INPUT_IMAGE_UNAVAILABLE,
    VideoTaskBlockingIssue.START_FRAME_NOT_IMAGE,
    VideoTaskBlockingIssue.END_FRAME_NOT_IMAGE,
    VideoTaskBlockingIssue.INPUT_IMAGE_NOT_IMAGE,
    VideoTaskBlockingIssue.MISSING_PROMPT,
    VideoTaskBlockingIssue.INVALID_DURATION,
    VideoTaskBlockingIssue.INVALID_FPS,
    VideoTaskBlockingIssue.INVALID_DIMENSIONS,
    VideoTaskBlockingIssue.INVALID_SEED,
    VideoTaskBlockingIssue.WORKFLOW_NOT_SELECTED,
    VideoTaskBlockingIssue.WORKFLOW_UNAVAILABLE,
    VideoTaskBlockingIssue.WORKFLOW_REQUIRES_END_FRAME,
]

WARNING_ORDER = [
    VideoTaskWarning.NO_NEGATIVE_PROMPT,
    VideoTaskWarning.NO_CAMERA_MOTION,
    VideoTaskWarning.NO_SEED,
    VideoTaskWarning.LOW_RESOLUTION,
    VideoTaskWarning.HIGH_ESTIMATED_RUNTIME,
    VideoTaskWarning.SAME_START_AND_END_FRAME,
]


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _valid_dimension(value: int) -> bool:
    return 256 <= value <= 2048 and value % 8 == 0


def _missing_issue(role: VideoInputRole) -> VideoTaskBlockingIssue:
    if role == VideoInputRole.END_FRAME:
        return VideoTaskBlockingIssue.MISSING_END_FRAME
    return VideoTaskBlockingIssue.MISSING_START_FRAME


def _unavailable_issue(role: VideoInputRole) -> VideoTaskBlockingIssue:
    if role == VideoInputRole.END_FRAME:
        return VideoTaskBlockingIssue.END_FRAME_UNAVAILABLE
    return VideoTaskBlockingIssue.START_FRAME_UNAVAILABLE


def _not_image_issue(role: VideoInputRole) -> VideoTaskBlockingIssue:
    if role == VideoInputRole.END_FRAME:
        return VideoTaskBlockingIssue.END_FRAME_NOT_IMAGE
    return VideoTaskBlockingIssue.START_FRAME_NOT_IMAGE
