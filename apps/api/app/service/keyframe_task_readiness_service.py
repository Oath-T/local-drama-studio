from datetime import UTC, datetime

from app.api.schemas.keyframe_task import (
    KeyframeShotSnapshot,
    KeyframeTaskReadinessResponse,
)
from app.domain.keyframe_task import (
    BLOCKING_ISSUE_ORDER,
    WARNING_ISSUE_ORDER,
    KeyframeTaskAspectRatio,
    KeyframeTaskBlockingIssue,
    KeyframeTaskReadinessStatus,
    KeyframeTaskWarningIssue,
    aspect_ratio_matches,
    is_valid_dimension,
)
from app.domain.media_asset import ALLOWED_IMAGE_MIME_TYPES, MediaType
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
    KeyframeGenerationTaskReferenceRecord,
)
from app.infrastructure.models.shot import ShotRecord
from app.service.media_storage_service import MediaStorageService


class KeyframeTaskReadinessService:
    def __init__(self, storage_service: MediaStorageService | None = None) -> None:
        self.storage_service = storage_service or MediaStorageService()

    def calculate(
        self,
        task: KeyframeGenerationTaskRecord,
        snapshot: KeyframeShotSnapshot,
        references: list[KeyframeGenerationTaskReferenceRecord],
        media_assets: dict[str, MediaAssetRecord],
        current_shot: ShotRecord | None,
    ) -> KeyframeTaskReadinessResponse:
        blocking: set[KeyframeTaskBlockingIssue] = set()
        warnings: set[KeyframeTaskWarningIssue] = set()

        if not self._has_text(task.name):
            blocking.add(KeyframeTaskBlockingIssue.MISSING_NAME)
        if not self._has_text(task.prompt_zh) and not self._has_text(task.prompt_en):
            blocking.add(KeyframeTaskBlockingIssue.NO_PROMPT)
        if not is_valid_dimension(task.width) or not is_valid_dimension(task.height):
            blocking.add(KeyframeTaskBlockingIssue.INVALID_DIMENSIONS)
        elif not aspect_ratio_matches(
            KeyframeTaskAspectRatio(task.aspect_ratio), task.width, task.height
        ):
            blocking.add(KeyframeTaskBlockingIssue.ASPECT_RATIO_MISMATCH)
        if not 1 <= task.steps <= 150:
            blocking.add(KeyframeTaskBlockingIssue.INVALID_STEPS)
        if not 0 <= task.guidance_scale <= 30:
            blocking.add(KeyframeTaskBlockingIssue.INVALID_GUIDANCE)
        if not 1 <= task.output_count <= 8:
            blocking.add(KeyframeTaskBlockingIssue.INVALID_OUTPUT_COUNT)

        self._check_character_references(snapshot, references, blocking, warnings)
        self._check_scene_references(snapshot, references, blocking, warnings)
        if self._has_unavailable_media(references, media_assets):
            blocking.add(KeyframeTaskBlockingIssue.UNAVAILABLE_MEDIA)

        if not self._has_text(task.prompt_en):
            warnings.add(KeyframeTaskWarningIssue.NO_ENGLISH_PROMPT)
        if not self._has_text(task.negative_prompt):
            warnings.add(KeyframeTaskWarningIssue.NO_NEGATIVE_PROMPT)
        if not self._has_text(task.model_name):
            warnings.add(KeyframeTaskWarningIssue.NO_MODEL_SELECTED)
        if self.shot_changed_since_snapshot(task, current_shot):
            warnings.add(KeyframeTaskWarningIssue.SHOT_CHANGED_SINCE_SNAPSHOT)
        if not any(
            reference.reference_type == "character" and reference.purpose == "identity"
            for reference in references
        ):
            warnings.add(KeyframeTaskWarningIssue.NO_IDENTITY_REFERENCE)
        if snapshot.scene_state_id and not any(
            reference.reference_type == "scene" and reference.purpose == "spatial"
            for reference in references
        ):
            warnings.add(KeyframeTaskWarningIssue.NO_SPATIAL_REFERENCE)
        if task.seed is None:
            warnings.add(KeyframeTaskWarningIssue.NO_SEED)

        ordered_blocking = [issue for issue in BLOCKING_ISSUE_ORDER if issue in blocking]
        ordered_warnings = [issue for issue in WARNING_ISSUE_ORDER if issue in warnings]
        return KeyframeTaskReadinessResponse(
            readiness_status=(
                KeyframeTaskReadinessStatus.READY
                if not ordered_blocking
                else KeyframeTaskReadinessStatus.INCOMPLETE
            ),
            blocking_issues=ordered_blocking,
            warnings=ordered_warnings,
        )

    @staticmethod
    def shot_changed_since_snapshot(
        task: KeyframeGenerationTaskRecord, current_shot: ShotRecord | None
    ) -> bool:
        if current_shot is None:
            return False
        return ensure_utc(current_shot.updated_at) > ensure_utc(task.source_shot_updated_at)

    @staticmethod
    def _check_character_references(
        snapshot: KeyframeShotSnapshot,
        references: list[KeyframeGenerationTaskReferenceRecord],
        blocking: set[KeyframeTaskBlockingIssue],
        warnings: set[KeyframeTaskWarningIssue],
    ) -> None:
        character_reference_source_ids = {
            reference.source_shot_character_id
            for reference in references
            if reference.reference_type == "character" and reference.source_shot_character_id
        }
        primary_characters = [
            character for character in snapshot.characters if character.is_primary_subject
        ]
        for character in primary_characters:
            if character.shot_character_id not in character_reference_source_ids:
                blocking.add(KeyframeTaskBlockingIssue.MISSING_PRIMARY_CHARACTER_REFERENCE)
                break
        secondary_characters = [
            character for character in snapshot.characters if not character.is_primary_subject
        ]
        for character in secondary_characters:
            if character.shot_character_id not in character_reference_source_ids:
                warnings.add(KeyframeTaskWarningIssue.MISSING_SECONDARY_CHARACTER_REFERENCE)
                break

    @staticmethod
    def _check_scene_references(
        snapshot: KeyframeShotSnapshot,
        references: list[KeyframeGenerationTaskReferenceRecord],
        blocking: set[KeyframeTaskBlockingIssue],
        warnings: set[KeyframeTaskWarningIssue],
    ) -> None:
        del warnings
        if not snapshot.scene_state_id:
            return
        has_matching_scene_reference = any(
            reference.reference_type == "scene"
            and reference.source_scene_state_id == snapshot.scene_state_id
            for reference in references
        )
        if not has_matching_scene_reference:
            blocking.add(KeyframeTaskBlockingIssue.MISSING_SCENE_REFERENCE)

    def _has_unavailable_media(
        self,
        references: list[KeyframeGenerationTaskReferenceRecord],
        media_assets: dict[str, MediaAssetRecord],
    ) -> bool:
        checked: set[str] = set()
        for reference in references:
            if reference.media_asset_id in checked:
                continue
            checked.add(reference.media_asset_id)
            media_asset = media_assets.get(reference.media_asset_id)
            if media_asset is None:
                return True
            if media_asset.media_type != MediaType.IMAGE.value:
                return True
            if media_asset.mime_type not in ALLOWED_IMAGE_MIME_TYPES:
                return True
            try:
                self.storage_service.resolve_relative_path(
                    media_asset.relative_path,
                    must_exist=True,
                )
            except Exception:
                return True
        return False

    @staticmethod
    def _has_text(value: str | None) -> bool:
        return bool(value and value.strip())


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
