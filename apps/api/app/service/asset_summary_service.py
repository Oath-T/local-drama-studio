from datetime import UTC, datetime
from uuid import UUID

from fastapi import status

from app.api.schemas.asset_summary import (
    CharacterAssetSummaryResponse,
    RecentShotSummary,
    SceneAssetSummaryResponse,
    ShotAssetCharacterSummary,
    ShotAssetSceneSummary,
    ShotAssetSummaryResponse,
    ShotGenerationAssetSummary,
    SummaryMediaAsset,
    SummaryReference,
)
from app.core.errors import AppError
from app.infrastructure.models.character import (
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import ShotReferenceRecord
from app.repository.asset_summary_repository import (
    AssetSummaryRepository,
    CharacterAssetSummaryData,
    SceneAssetSummaryData,
    ShotAssetSummaryData,
)

FEATURED_REFERENCE_LIMIT = 8


class AssetSummaryService:
    def __init__(self, repository: AssetSummaryRepository) -> None:
        self.repository = repository

    def get_character_summary(
        self, project_id: UUID, character_id: UUID
    ) -> CharacterAssetSummaryResponse:
        self._ensure_project(project_id)
        data = self.repository.get_character_summary(str(project_id), str(character_id))
        if data is None:
            raise_not_found("CHARACTER_NOT_FOUND", "角色不存在或已被删除。")
        return self._character_summary_response(data)

    def get_scene_summary(self, project_id: UUID, scene_id: UUID) -> SceneAssetSummaryResponse:
        self._ensure_project(project_id)
        data = self.repository.get_scene_summary(str(project_id), str(scene_id))
        if data is None:
            raise_not_found("SCENE_NOT_FOUND", "场景不存在或已被删除。")
        return self._scene_summary_response(data)

    def get_shot_summary(self, project_id: UUID, shot_id: UUID) -> ShotAssetSummaryResponse:
        self._ensure_project(project_id)
        data = self.repository.get_shot_summary(str(project_id), str(shot_id))
        if data is None:
            raise_not_found("SHOT_NOT_FOUND", "镜头不存在或已被删除。")
        return self._shot_summary_response(data)

    def _character_summary_response(
        self, data: CharacterAssetSummaryData
    ) -> CharacterAssetSummaryResponse:
        default_look = data.looks[0] if data.looks else None
        identity_count = sum(1 for reference in data.references if reference.is_identity_anchor)
        primary_count = sum(1 for reference in data.references if reference.is_primary)
        face_count = sum(
            1
            for reference in data.references
            if reference.shot_type in {"face_closeup", "closeup", "upper_body"}
        )
        full_body_count = sum(
            1
            for reference in data.references
            if reference.shot_type in {"full_body", "three_quarter"}
        )
        warnings: list[str] = []
        if not data.looks:
            warnings.append("缺少默认造型")
        if identity_count == 0:
            warnings.append("缺少身份基准图")
        if primary_count == 0:
            warnings.append("缺少主参考图")
        if full_body_count == 0:
            warnings.append("缺少全身或大半身造型参考")
        return CharacterAssetSummaryResponse(
            id=data.character.id,
            project_id=data.character.project_id,
            name=data.character.name,
            default_look_id=default_look.id if default_look else None,
            default_look_name=default_look.name if default_look else None,
            look_count=len(data.looks),
            reference_count=len(data.references),
            primary_reference_count=primary_count,
            identity_anchor_count=identity_count,
            face_reference_count=face_count,
            full_body_reference_count=full_body_count,
            used_shot_count=data.used_shot_count,
            recent_shots=[recent_shot_response(shot) for shot in data.recent_shots],
            featured_references=[
                character_reference_summary(reference)
                for reference in data.references[:FEATURED_REFERENCE_LIMIT]
            ],
            completeness_warnings=warnings,
        )

    def _scene_summary_response(self, data: SceneAssetSummaryData) -> SceneAssetSummaryResponse:
        default_state = data.states[0] if data.states else None
        primary_count = sum(1 for reference in data.references if reference.is_primary)
        spatial_count = sum(1 for reference in data.references if reference.is_spatial_anchor)
        empty_count = sum(1 for reference in data.references if reference.is_empty_plate)
        wide_count = sum(
            1
            for reference in data.references
            if reference.shot_scale in {"extreme_wide", "wide", "full", "medium_wide"}
        )
        warnings: list[str] = []
        if not data.states:
            warnings.append("缺少默认场景状态")
        if spatial_count == 0:
            warnings.append("缺少空间结构参考图")
        if empty_count == 0:
            warnings.append("缺少空镜参考")
        if primary_count == 0:
            warnings.append("缺少主参考图")
        return SceneAssetSummaryResponse(
            id=data.scene.id,
            project_id=data.scene.project_id,
            name=data.scene.name,
            default_state_id=default_state.id if default_state else None,
            default_state_name=default_state.name if default_state else None,
            state_count=len(data.states),
            reference_count=len(data.references),
            primary_reference_count=primary_count,
            spatial_anchor_count=spatial_count,
            empty_plate_count=empty_count,
            wide_reference_count=wide_count,
            used_shot_count=data.used_shot_count,
            recent_shots=[recent_shot_response(shot) for shot in data.recent_shots],
            featured_references=[
                scene_reference_summary(reference)
                for reference in data.references[:FEATURED_REFERENCE_LIMIT]
            ],
            completeness_warnings=warnings,
        )

    def _shot_summary_response(self, data: ShotAssetSummaryData) -> ShotAssetSummaryResponse:
        character_records = self.repository.get_characters_by_ids(
            [character.character_id for character in data.characters]
        )
        look_records = self.repository.get_looks_by_ids(
            [character.look_id for character in data.characters if character.look_id]
        )
        character_reference_records = self.repository.get_character_references_by_ids(
            [
                reference.character_reference_id
                for reference in data.references
                if reference.character_reference_id
            ]
        )
        scene_reference_records = self.repository.get_scene_references_by_ids(
            [
                reference.scene_reference_id
                for reference in data.references
                if reference.scene_reference_id
            ]
        )
        media_asset_records = self.repository.get_media_assets_by_ids(
            [reference.media_asset_id for reference in data.references if reference.media_asset_id]
        )

        reference_counts_by_shot_character: dict[str, int] = {}
        scene_reference_count = 0
        for reference in data.references:
            if reference.reference_type == "scene":
                scene_reference_count += 1
            if reference.shot_character_id:
                reference_counts_by_shot_character[reference.shot_character_id] = (
                    reference_counts_by_shot_character.get(reference.shot_character_id, 0) + 1
                )

        characters: list[ShotAssetCharacterSummary] = []
        for shot_character in data.characters:
            character = character_records.get(shot_character.character_id)
            look = look_records.get(shot_character.look_id or "")
            warnings: list[str] = []
            if shot_character.look_id is None:
                warnings.append("缺少指定造型")
            if reference_counts_by_shot_character.get(shot_character.id, 0) == 0:
                warnings.append("缺少人物参考图")
            characters.append(
                ShotAssetCharacterSummary(
                    shot_character_id=shot_character.id,
                    character_id=shot_character.character_id,
                    character_name=character.name if character else "已删除角色",
                    look_id=shot_character.look_id,
                    look_name=look.name if look else None,
                    is_primary_subject=shot_character.is_primary_subject,
                    bound_reference_count=reference_counts_by_shot_character.get(
                        shot_character.id, 0
                    ),
                    completeness_warnings=warnings,
                )
            )

        scene_warnings: list[str] = []
        if data.shot.scene_id is None:
            scene_warnings.append("缺少场景")
        if data.shot.scene_state_id is None:
            scene_warnings.append("缺少场景状态")
        if data.shot.scene_state_id and scene_reference_count == 0:
            scene_warnings.append("缺少场景参考图")

        all_warnings: list[str] = []
        if not characters:
            all_warnings.append("缺少参与人物")
        all_warnings.extend(scene_warnings)
        for character in characters:
            all_warnings.extend(character.completeness_warnings)

        references: list[SummaryReference] = []
        for shot_reference in data.references:
            references.append(
                shot_reference_summary(
                    shot_reference,
                    character_reference_records.get(shot_reference.character_reference_id or ""),
                    scene_reference_records.get(shot_reference.scene_reference_id or ""),
                    media_asset_records.get(shot_reference.media_asset_id or ""),
                )
            )

        return ShotAssetSummaryResponse(
            id=data.shot.id,
            project_id=data.shot.project_id,
            name=data.shot.name,
            characters=characters,
            scene=ShotAssetSceneSummary(
                scene_id=data.shot.scene_id,
                scene_name=data.scene.name if data.scene else None,
                scene_state_id=data.shot.scene_state_id,
                scene_state_name=data.state.name if data.state else None,
                bound_reference_count=scene_reference_count,
                completeness_warnings=scene_warnings,
            ),
            references=references,
            generation=ShotGenerationAssetSummary(
                keyframe_task_count=data.keyframe_task_count,
                video_task_count=data.video_task_count,
                selected_keyframe_output_count=data.selected_keyframe_output_count,
                selected_video_output_count=data.selected_video_output_count,
            ),
            completeness_warnings=unique_strings(all_warnings),
        )

    def _ensure_project(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_not_found("PROJECT_NOT_FOUND", "项目不存在或已被删除。")


def media_asset_summary(media_asset: MediaAssetRecord | None) -> SummaryMediaAsset | None:
    if media_asset is None:
        return None
    return SummaryMediaAsset(
        id=media_asset.id,
        media_type=media_asset.media_type,
        original_filename=media_asset.original_filename,
        mime_type=media_asset.mime_type,
        width=media_asset.width,
        height=media_asset.height,
        thumbnail_url=f"/api/media/{media_asset.id}/thumbnail"
        if media_asset.thumbnail_relative_path
        else None,
        content_url=f"/api/media/{media_asset.id}/content",
        created_at=ensure_utc(media_asset.created_at),
    )


def character_reference_summary(reference: CharacterReferenceRecord) -> SummaryReference:
    label = reference.description or reference.media_asset.original_filename
    return SummaryReference(
        id=reference.id,
        reference_type="character",
        label=label,
        look_id=reference.look_id,
        look_name=reference.look.name if reference.look else None,
        is_primary=reference.is_primary,
        is_identity_anchor=reference.is_identity_anchor,
        media_asset=media_asset_summary(reference.media_asset),
        created_at=ensure_utc(reference.created_at),
    )


def scene_reference_summary(reference: SceneReferenceRecord) -> SummaryReference:
    label = reference.description or reference.media_asset.original_filename
    return SummaryReference(
        id=reference.id,
        reference_type="scene",
        label=label,
        state_id=reference.state_id,
        state_name=reference.state.name if reference.state else None,
        is_primary=reference.is_primary,
        is_spatial_anchor=reference.is_spatial_anchor,
        is_empty_plate=reference.is_empty_plate,
        media_asset=media_asset_summary(reference.media_asset),
        created_at=ensure_utc(reference.created_at),
    )


def shot_reference_summary(
    shot_reference: ShotReferenceRecord,
    character_reference: CharacterReferenceRecord | None,
    scene_reference: SceneReferenceRecord | None,
    media_asset: MediaAssetRecord | None = None,
) -> SummaryReference:
    if shot_reference.reference_type == "character":
        reference = character_reference
        return SummaryReference(
            id=shot_reference.id,
            reference_type="character",
            label=reference_label(reference),
            purpose=shot_reference.purpose,
            look_id=reference.look_id if reference else None,
            look_name=reference.look.name if reference and reference.look else None,
            is_primary=reference.is_primary if reference else False,
            is_identity_anchor=reference.is_identity_anchor if reference else False,
            media_asset=media_asset_summary(reference.media_asset if reference else None),
            created_at=ensure_utc(shot_reference.created_at),
        )
    if shot_reference.reference_type == "media":
        return SummaryReference(
            id=shot_reference.id,
            reference_type="media",
            label=media_asset.original_filename if media_asset else "源参考图已删除",
            purpose=shot_reference.purpose,
            media_asset=media_asset_summary(media_asset),
            created_at=ensure_utc(shot_reference.created_at),
        )
    reference = scene_reference
    return SummaryReference(
        id=shot_reference.id,
        reference_type="scene",
        label=reference_label(reference),
        purpose=shot_reference.purpose,
        state_id=reference.state_id if reference else None,
        state_name=reference.state.name if reference and reference.state else None,
        is_primary=reference.is_primary if reference else False,
        is_spatial_anchor=reference.is_spatial_anchor if reference else False,
        is_empty_plate=reference.is_empty_plate if reference else False,
        media_asset=media_asset_summary(reference.media_asset if reference else None),
        created_at=ensure_utc(shot_reference.created_at),
    )


def reference_label(
    reference: CharacterReferenceRecord | SceneReferenceRecord | None,
) -> str:
    if reference is None:
        return "源参考图已删除"
    return reference.description or reference.media_asset.original_filename


def recent_shot_response(shot: object) -> RecentShotSummary:
    return RecentShotSummary(
        id=shot.id,
        name=shot.name,
        order_index=shot.order_index,
        updated_at=ensure_utc(shot.updated_at),
    )


def unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def raise_not_found(code: str, message: str) -> None:
    raise AppError(code=code, message=message, status_code=status.HTTP_404_NOT_FOUND)
