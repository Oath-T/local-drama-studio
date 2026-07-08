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
    CharacterLookPickerData,
    CharacterPickerData,
    FrameImagePickerData,
    ReferenceImagePickerData,
    ScenePickerData,
    SceneStatePickerData,
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
        character_id: UUID | None,
        scene_id: UUID | None,
        shot_character_id: UUID | None,
        task_id: UUID | None,
        source: str | None,
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
        elif asset_type == "character_look":
            if character_id is None:
                raise AppError(
                    code="CHARACTER_ID_REQUIRED",
                    message="选择人物造型时需要提供角色 ID。",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            character_id_text = str(character_id)
            if not self.repository.character_exists(project_id_text, character_id_text):
                raise AppError(
                    code="CHARACTER_NOT_FOUND",
                    message="角色不存在或已被删除。",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            data = self.repository.list_character_look_options(
                project_id_text,
                character_id=character_id_text,
                shot_character_id=str(shot_character_id) if shot_character_id else None,
                q=query,
                limit=normalized_limit,
            )
            items = [character_look_item(item) for item in data]
        elif asset_type == "scene_state":
            if scene_id is None:
                raise AppError(
                    code="SCENE_ID_REQUIRED",
                    message="选择场景状态时需要提供场景 ID。",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            scene_id_text = str(scene_id)
            if not self.repository.scene_exists(project_id_text, scene_id_text):
                raise AppError(
                    code="SCENE_NOT_FOUND",
                    message="场景不存在或已被删除。",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            data = self.repository.list_scene_state_options(
                project_id_text,
                scene_id=scene_id_text,
                shot_id=shot_id_text,
                q=query,
                limit=normalized_limit,
            )
            items = [scene_state_item(item) for item in data]
        elif asset_type == "reference_image":
            if scope != "shot" or shot_id_text is None:
                raise AppError(
                    code="SHOT_ID_REQUIRED",
                    message="按镜头选择参考图时需要提供镜头 ID。",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            if source not in (None, "shot_context"):
                raise AppError(
                    code="UNSUPPORTED_PICKER_SOURCE",
                    message="当前参考图来源暂不支持。",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            data = self.repository.list_reference_image_options(
                project_id_text,
                shot_id=shot_id_text,
                task_id=str(task_id) if task_id else None,
                q=query,
                limit=normalized_limit,
            )
            items = [reference_image_item(item) for item in data]
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


def character_look_item(data: CharacterLookPickerData) -> PickerOptionItem:
    badges: list[str] = []
    if data.look.is_default:
        badges.append("默认造型")
    if data.is_selected:
        badges.append("当前使用")
    badges.append(f"{data.reference_count} 张参考图")
    media = data.cover_reference.media_asset if data.cover_reference else None
    description = first_text(
        data.look.description,
        data.look.costume_description,
        data.look.prompt_appearance,
    )
    return PickerOptionItem(
        id=data.look.id,
        type="character_look",
        name=data.look.name,
        description=description,
        thumbnail_url=thumbnail_url(media),
        content_url=content_url(media),
        badges=badges,
        source=PickerOptionSource(kind="character_look", label="人物造型"),
        is_selected=data.is_selected,
        metadata={
            "character_id": data.look.character_id,
            "reference_count": data.reference_count,
            "is_default": data.look.is_default,
        },
    )


def scene_state_item(data: SceneStatePickerData) -> PickerOptionItem:
    badges: list[str] = []
    if data.state.is_default:
        badges.append("默认状态")
    if data.is_selected:
        badges.append("当前使用")
    badges.append(f"{data.reference_count} 张参考图")
    media = data.cover_reference.media_asset if data.cover_reference else None
    description = first_text(
        data.state.description,
        data.state.environment_condition,
        data.state.prompt_state,
    )
    return PickerOptionItem(
        id=data.state.id,
        type="scene_state",
        name=data.state.name,
        description=description,
        thumbnail_url=thumbnail_url(media),
        content_url=content_url(media),
        badges=badges,
        source=PickerOptionSource(kind="scene_state", label="场景状态"),
        is_selected=data.is_selected,
        metadata={
            "scene_id": data.state.scene_id,
            "reference_count": data.reference_count,
            "is_default": data.state.is_default,
            "time_of_day": data.state.time_of_day,
            "weather": data.state.weather,
            "lighting": data.state.lighting,
            "season": data.state.season,
            "crowd_level": data.state.crowd_level,
        },
    )


def reference_image_item(data: ReferenceImagePickerData) -> PickerOptionItem:
    badges = [data.source_label]
    extra_badges = data.metadata.get("source_badges")
    if isinstance(extra_badges, str) and extra_badges:
        badges.extend([badge for badge in extra_badges.split(",") if badge])
    if data.metadata.get("is_bound_to_shot"):
        badges.append("已绑定")
    if data.metadata.get("is_added_to_task"):
        badges.append("已加入任务")
    return PickerOptionItem(
        id=data.id,
        type="reference_image",
        name=data.name,
        description=data.description,
        thumbnail_url=thumbnail_url(data.media_asset),
        content_url=content_url(data.media_asset),
        badges=badges,
        source=PickerOptionSource(kind=data.source_kind, label=data.source_label),
        is_selected=data.is_selected,
        metadata={key: value for key, value in data.metadata.items() if key != "source_badges"},
    )


def first_text(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def thumbnail_url(media_asset: MediaAssetRecord | None) -> str | None:
    if media_asset is None or not media_asset.thumbnail_relative_path:
        return None
    return f"/api/media/{media_asset.id}/thumbnail"


def content_url(media_asset: MediaAssetRecord | None) -> str | None:
    if media_asset is None:
        return None
    return f"/api/media/{media_asset.id}/content"
