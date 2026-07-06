from uuid import UUID

from fastapi import status

from app.api.schemas.asset_picker import (
    PickerOptionItem,
    PickerOptionListResponse,
    PickerOptionSource,
)
from app.core.errors import AppError
from app.infrastructure.models.character import MediaAssetRecord
from app.repository.asset_picker_repository import (
    AssetPickerRepository,
    CharacterPickerData,
    FrameImagePickerData,
    ScenePickerData,
)

DEFAULT_LIMIT = 40
MAX_LIMIT = 80


class AssetPickerService:
    def __init__(self, repository: AssetPickerRepository) -> None:
        self.repository = repository

    def list_options(
        self,
        project_id: UUID,
        *,
        scope: str,
        asset_type: str,
        shot_id: UUID | None,
        q: str | None,
        limit: int | None,
    ) -> PickerOptionListResponse:
        project_id_text = str(project_id)
        if not self.repository.project_exists(project_id_text):
            raise AppError(
                code="PROJECT_NOT_FOUND",
                message="项目不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if scope == "shot" and shot_id is None:
            raise AppError(
                code="SHOT_ID_REQUIRED",
                message="按镜头选择资产时需要提供镜头 ID。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        shot_id_text = str(shot_id) if shot_id else None
        if shot_id_text:
            shot = self.repository.get_shot(project_id_text, shot_id_text)
            if shot is None:
                raise AppError(
                    code="SHOT_NOT_FOUND",
                    message="镜头不存在或已被删除。",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        normalized_limit = max(1, min(limit or DEFAULT_LIMIT, MAX_LIMIT))
        query = q.strip() if q and q.strip() else None

        if asset_type == "character":
            data = self.repository.list_character_options(
                project_id_text,
                shot_id=shot_id_text,
                q=query,
                limit=normalized_limit,
            )
            items = [character_item(item) for item in data]
        elif asset_type == "scene":
            data = self.repository.list_scene_options(
                project_id_text,
                shot_id=shot_id_text,
                q=query,
                limit=normalized_limit,
            )
            items = [scene_item(item) for item in data]
        elif asset_type == "frame_image":
            if shot_id_text is None:
                raise AppError(
                    code="SHOT_ID_REQUIRED",
                    message="选择视频首尾帧时需要提供镜头 ID。",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            data = self.repository.list_frame_image_options(
                project_id_text,
                shot_id=shot_id_text,
                q=query,
                limit=normalized_limit,
            )
            items = [frame_image_item(item) for item in data]
        else:
            raise AppError(
                code="UNSUPPORTED_PICKER_ASSET_TYPE",
                message="当前资产类型暂不支持选择。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return PickerOptionListResponse(items=items, total=len(items))


def character_item(data: CharacterPickerData) -> PickerOptionItem:
    badges: list[str] = []
    if data.default_look:
        badges.append(f"默认造型：{data.default_look.name}")
    if data.has_identity_anchor:
        badges.append("身份基准图")
    if data.is_selected:
        badges.append("已绑定")
    media = data.cover_reference.media_asset if data.cover_reference else None
    return PickerOptionItem(
        id=data.character.id,
        type="character",
        name=data.character.name,
        description=data.character.description,
        thumbnail_url=thumbnail_url(media),
        content_url=content_url(media),
        badges=badges,
        source=PickerOptionSource(kind="character", label="人物库"),
        is_selected=data.is_selected,
        metadata={
            "default_look_id": data.default_look.id if data.default_look else None,
            "default_look_name": data.default_look.name if data.default_look else None,
            "reference_count": data.reference_count,
            "has_identity_anchor": data.has_identity_anchor,
        },
    )


def scene_item(data: ScenePickerData) -> PickerOptionItem:
    badges: list[str] = []
    if data.default_state:
        badges.append(f"默认状态：{data.default_state.name}")
    if data.has_spatial_anchor:
        badges.append("空间结构参考图")
    if data.is_selected:
        badges.append("当前使用")
    media = data.cover_reference.media_asset if data.cover_reference else None
    return PickerOptionItem(
        id=data.scene.id,
        type="scene",
        name=data.scene.name,
        description=data.scene.description or data.scene.fixed_environment_description,
        thumbnail_url=thumbnail_url(media),
        content_url=content_url(media),
        badges=badges,
        source=PickerOptionSource(kind="scene", label="场景库"),
        is_selected=data.is_selected,
        metadata={
            "default_state_id": data.default_state.id if data.default_state else None,
            "default_state_name": data.default_state.name if data.default_state else None,
            "reference_count": data.reference_count,
            "has_spatial_anchor": data.has_spatial_anchor,
        },
    )


def frame_image_item(data: FrameImagePickerData) -> PickerOptionItem:
    return PickerOptionItem(
        id=data.id,
        type="frame_image",
        name=data.name,
        description=data.description,
        thumbnail_url=thumbnail_url(data.media_asset),
        content_url=content_url(data.media_asset),
        badges=[data.source_label, *([] if not data.is_adopted else ["已采用"])],
        source=PickerOptionSource(
            kind="keyframe_output" if "keyframe_output_id" in data.metadata else "media_asset",
            label=data.source_label,
        ),
        is_adopted=data.is_adopted,
        metadata={**data.metadata, "media_asset_id": data.media_asset.id},
    )


def thumbnail_url(media_asset: MediaAssetRecord | None) -> str | None:
    if media_asset is None or not media_asset.thumbnail_relative_path:
        return None
    return f"/api/media/{media_asset.id}/thumbnail"


def content_url(media_asset: MediaAssetRecord | None) -> str | None:
    if media_asset is None:
        return None
    return f"/api/media/{media_asset.id}/content"
