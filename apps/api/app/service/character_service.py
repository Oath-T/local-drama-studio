import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import UploadFile, status

from app.api.schemas.character import (
    CharacterCreateRequest,
    CharacterListResponse,
    CharacterLookCreateRequest,
    CharacterLookListResponse,
    CharacterLookResponse,
    CharacterLookUpdateRequest,
    CharacterReferenceListResponse,
    CharacterReferenceResponse,
    CharacterReferenceUpdateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
    MediaAssetResponse,
    VisionAnalysisSuggestion,
)
from app.core.errors import AppError
from app.domain.character import (
    AnalysisStatus,
    CharacterErrorCode,
    Expression,
    PoseType,
    RoleType,
    ShotType,
    SuggestionReviewStatus,
    ViewAngle,
    normalize_optional_text,
    normalize_required_text,
    normalize_tags,
)
from app.domain.media_asset import MediaType
from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.repository.character_repository import CharacterRepository
from app.service.media_storage_service import MediaStorageService, StoredImage

ERROR_MESSAGES: dict[CharacterErrorCode, str] = {
    CharacterErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    CharacterErrorCode.CHARACTER_NOT_FOUND: "角色不存在或已被删除。",
    CharacterErrorCode.LOOK_NOT_FOUND: "造型不存在或已被删除。",
    CharacterErrorCode.REFERENCE_NOT_FOUND: "参考图不存在或已被删除。",
    CharacterErrorCode.MEDIA_NOT_FOUND: "媒体文件不存在或已被删除。",
    CharacterErrorCode.NAME_REQUIRED: "请输入角色名称。",
    CharacterErrorCode.NAME_TOO_LONG: "角色名称不能超过 100 个字符。",
    CharacterErrorCode.LOOK_NAME_REQUIRED: "请输入造型名称。",
    CharacterErrorCode.LOOK_NAME_TOO_LONG: "造型名称不能超过 100 个字符。",
    CharacterErrorCode.INVALID_ROLE_TYPE: "请选择有效的角色类型。",
    CharacterErrorCode.INVALID_SHOT_TYPE: "请选择有效的景别。",
    CharacterErrorCode.INVALID_VIEW_ANGLE: "请选择有效的视角。",
    CharacterErrorCode.INVALID_EXPRESSION: "请选择有效的表情。",
    CharacterErrorCode.INVALID_POSE_TYPE: "请选择有效的姿势。",
    CharacterErrorCode.INVALID_ANALYSIS_STATUS: "分析状态无效。",
    CharacterErrorCode.INVALID_SUGGESTION_REVIEW_STATUS: "建议确认状态无效。",
    CharacterErrorCode.LAST_LOOK_DELETE_FORBIDDEN: "不能删除角色的最后一套造型。",
}

HTTP_422 = 422


class CharacterService:
    def __init__(
        self,
        repository: CharacterRepository,
        storage_service: MediaStorageService | None = None,
    ) -> None:
        self.repository = repository
        self.storage_service = storage_service or MediaStorageService()

    def list_characters(self, project_id: UUID) -> CharacterListResponse:
        self._ensure_project(project_id)
        characters, total = self.repository.list_characters(str(project_id))
        return CharacterListResponse(
            items=[self._character_response(character) for character in characters],
            total=total,
        )

    def create_character(
        self, project_id: UUID, payload: CharacterCreateRequest
    ) -> CharacterResponse:
        self._ensure_project(project_id)
        now = utc_now()
        character = CharacterRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            name=self._normalize_character_name(payload.name),
            aliases=self._optional(payload.aliases, 200),
            role_type=payload.role_type.value,
            description=self._optional(payload.description, 1000),
            appearance_description=self._optional(payload.appearance_description, 2000),
            personality_description=self._optional(payload.personality_description, 2000),
            prompt_identity=self._optional(payload.prompt_identity, 2000),
            notes=self._optional(payload.notes, 2000),
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_character(character)
        return self._character_response(created)

    def get_character(self, project_id: UUID, character_id: UUID) -> CharacterResponse:
        character = self._get_character(project_id, character_id)
        return self._character_response(character)

    def update_character(
        self,
        project_id: UUID,
        character_id: UUID,
        payload: CharacterUpdateRequest,
    ) -> CharacterResponse:
        character = self._get_character(project_id, character_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_character_name(submitted["name"])
        for key, max_length in {
            "aliases": 200,
            "description": 1000,
            "appearance_description": 2000,
            "personality_description": 2000,
            "prompt_identity": 2000,
            "notes": 2000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "role_type" in submitted and submitted["role_type"] is not None:
            values["role_type"] = submitted["role_type"].value
        values["updated_at"] = utc_now()
        updated = self.repository.update_character(character, values)
        return self._character_response(updated)

    def delete_character(self, project_id: UUID, character_id: UUID) -> None:
        character = self._get_character(project_id, character_id)
        references = self._all_character_references(character.id)
        media_assets = [reference.media_asset for reference in references]
        media_asset_ids = [media_asset.id for media_asset in media_assets]
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            media_asset_ids
        )
        deletable_media_ids = [
            media_asset_id
            for media_asset_id in media_asset_ids
            if media_asset_id not in protected_media_ids
        ]
        self.repository.delete_character_and_media_assets(character, deletable_media_ids)
        for media_asset in media_assets:
            if media_asset.id in protected_media_ids:
                continue
            self._delete_media_files_safely(media_asset)

    def list_looks(self, project_id: UUID, character_id: UUID) -> CharacterLookListResponse:
        self._get_character(project_id, character_id)
        looks, total = self.repository.list_looks(str(character_id))
        return CharacterLookListResponse(
            items=[self._look_response(look) for look in looks],
            total=total,
        )

    def create_look(
        self,
        project_id: UUID,
        character_id: UUID,
        payload: CharacterLookCreateRequest,
    ) -> CharacterLookResponse:
        self._get_character(project_id, character_id)
        existing, _ = self.repository.list_looks(str(character_id))
        now = utc_now()
        look = CharacterLookRecord(
            id=str(uuid4()),
            character_id=str(character_id),
            name=self._normalize_look_name(payload.name),
            description=self._optional(payload.description, 1000),
            costume_description=self._optional(payload.costume_description, 2000),
            hair_description=self._optional(payload.hair_description, 1000),
            makeup_description=self._optional(payload.makeup_description, 1000),
            condition_description=self._optional(payload.condition_description, 1000),
            prompt_appearance=self._optional(payload.prompt_appearance, 3000),
            is_default=len(existing) == 0,
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_look(look)
        return self._look_response(created)

    def get_look(
        self, project_id: UUID, character_id: UUID, look_id: UUID
    ) -> CharacterLookResponse:
        look = self._get_look(project_id, character_id, look_id)
        return self._look_response(look)

    def update_look(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        payload: CharacterLookUpdateRequest,
    ) -> CharacterLookResponse:
        look = self._get_look(project_id, character_id, look_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_look_name(submitted["name"])
        for key, max_length in {
            "description": 1000,
            "costume_description": 2000,
            "hair_description": 1000,
            "makeup_description": 1000,
            "condition_description": 1000,
            "prompt_appearance": 3000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        values["updated_at"] = utc_now()
        updated = self.repository.update_look(look, values)
        return self._look_response(updated)

    def set_default_look(
        self, project_id: UUID, character_id: UUID, look_id: UUID
    ) -> CharacterLookResponse:
        look = self._get_look(project_id, character_id, look_id)
        self.repository.clear_default_looks(str(character_id))
        updated = self.repository.update_look(look, {"is_default": True, "updated_at": utc_now()})
        return self._look_response(updated)

    def delete_look(self, project_id: UUID, character_id: UUID, look_id: UUID) -> None:
        look = self._get_look(project_id, character_id, look_id)
        looks, _ = self.repository.list_looks(str(character_id))
        if len(looks) <= 1:
            raise_character_error(
                CharacterErrorCode.LAST_LOOK_DELETE_FORBIDDEN,
                status.HTTP_400_BAD_REQUEST,
            )
        references, _ = self.repository.list_references(look.id)
        media_assets = [reference.media_asset for reference in references]
        next_default = self._select_next_default_look(look, looks)
        media_asset_ids = [media_asset.id for media_asset in media_assets]
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            media_asset_ids
        )
        deletable_media_ids = [
            media_asset_id
            for media_asset_id in media_asset_ids
            if media_asset_id not in protected_media_ids
        ]
        self.repository.delete_look_and_media_assets(look, deletable_media_ids, next_default)
        for media_asset in media_assets:
            if media_asset.id in protected_media_ids:
                continue
            self._delete_media_files_safely(media_asset)

    def list_references(
        self, project_id: UUID, character_id: UUID, look_id: UUID
    ) -> CharacterReferenceListResponse:
        look = self._get_look(project_id, character_id, look_id)
        references, total = self.repository.list_references(look.id)
        return CharacterReferenceListResponse(
            items=[self._reference_response(reference) for reference in references],
            total=total,
        )

    def get_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> CharacterReferenceResponse:
        reference = self._get_reference(project_id, character_id, look_id, reference_id)
        return self._reference_response(reference)

    async def upload_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        upload: UploadFile,
        payload: CharacterReferenceUpdateRequest,
    ) -> CharacterReferenceResponse:
        look = self._get_look(project_id, character_id, look_id)
        stored = await self.storage_service.store_reference_image(
            str(project_id), str(character_id), str(look_id), upload
        )
        references, _ = self.repository.list_references(look.id)
        now = utc_now()
        media_asset = self._media_asset_from_stored(stored, str(project_id), now)
        reference = CharacterReferenceRecord(
            id=str(uuid4()),
            look_id=look.id,
            media_asset_id=media_asset.id,
            shot_type=(payload.shot_type or ShotType.UNKNOWN).value,
            view_angle=(payload.view_angle or ViewAngle.UNKNOWN).value,
            expression=(payload.expression or Expression.UNKNOWN).value,
            pose_type=(payload.pose_type or PoseType.UNKNOWN).value,
            custom_expression=self._optional(payload.custom_expression, 100),
            custom_pose=self._optional(payload.custom_pose, 100),
            tags=json.dumps(normalize_tags(payload.tags), ensure_ascii=False),
            description=self._optional(payload.description, 1000),
            notes=self._optional(payload.notes, 1000),
            is_primary=len(references) == 0,
            is_identity_anchor=bool(payload.is_identity_anchor),
            analysis_status=AnalysisStatus.NOT_ANALYZED.value,
            suggestion_review_status=SuggestionReviewStatus.NOT_REVIEWED.value,
            analysis_suggestions=None,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_reference(media_asset, reference)
        except Exception:
            self.storage_service.delete_relative_file(stored.relative_path)
            self.storage_service.delete_relative_file(stored.thumbnail_relative_path)
            raise
        return self._reference_response(created)

    def update_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
        payload: CharacterReferenceUpdateRequest,
    ) -> CharacterReferenceResponse:
        reference = self._get_reference(project_id, character_id, look_id, reference_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        enum_fields = {
            "shot_type": ShotType,
            "view_angle": ViewAngle,
            "expression": Expression,
            "pose_type": PoseType,
        }
        for key in enum_fields:
            if key in submitted and submitted[key] is not None:
                values[key] = submitted[key].value
        for key, max_length in {
            "custom_expression": 100,
            "custom_pose": 100,
            "description": 1000,
            "notes": 1000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "tags" in submitted:
            values["tags"] = json.dumps(normalize_tags(submitted["tags"]), ensure_ascii=False)
        if "is_identity_anchor" in submitted:
            values["is_identity_anchor"] = bool(submitted["is_identity_anchor"])
        values["updated_at"] = utc_now()
        updated = self.repository.update_reference(reference, values)
        return self._reference_response(updated)

    def set_primary_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> CharacterReferenceResponse:
        reference = self._get_reference(project_id, character_id, look_id, reference_id)
        self.repository.clear_primary_references(str(look_id))
        updated = self.repository.update_reference(
            reference, {"is_primary": True, "updated_at": utc_now()}
        )
        return self._reference_response(updated)

    def delete_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> None:
        reference = self._get_reference(project_id, character_id, look_id, reference_id)
        media_asset = reference.media_asset
        references, _ = self.repository.list_references(str(look_id))
        next_primary = self._select_next_primary_reference(reference, references)
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            [media_asset.id]
        )
        delete_media_asset_id = None if media_asset.id in protected_media_ids else media_asset.id
        self.repository.delete_reference_and_media_asset(
            reference,
            delete_media_asset_id,
            next_primary,
        )
        if media_asset.id not in protected_media_ids:
            self._delete_media_files_safely(media_asset)

    def get_media_asset(self, media_asset_id: UUID) -> MediaAssetRecord:
        media_asset = self.repository.get_media_asset(str(media_asset_id))
        if media_asset is None:
            raise_character_error(CharacterErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return media_asset

    def resolve_media_file(
        self, media_asset_id: UUID, variant: str
    ) -> tuple[MediaAssetRecord, str]:
        media_asset = self.get_media_asset(media_asset_id)
        relative_path = (
            media_asset.thumbnail_relative_path
            if variant == "thumbnail"
            else media_asset.relative_path
        )
        return media_asset, relative_path

    def _ensure_project(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_character_error(CharacterErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    def _get_character(self, project_id: UUID, character_id: UUID) -> CharacterRecord:
        character = self.repository.get_character(str(project_id), str(character_id))
        if character is None:
            raise_character_error(CharacterErrorCode.CHARACTER_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return character

    def _get_look(self, project_id: UUID, character_id: UUID, look_id: UUID) -> CharacterLookRecord:
        self._get_character(project_id, character_id)
        look = self.repository.get_look(str(character_id), str(look_id))
        if look is None:
            raise_character_error(CharacterErrorCode.LOOK_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return look

    def _get_reference(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> CharacterReferenceRecord:
        self._get_look(project_id, character_id, look_id)
        reference = self.repository.get_reference(str(look_id), str(reference_id))
        if reference is None:
            raise_character_error(CharacterErrorCode.REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return reference

    def _all_character_references(self, character_id: str) -> list[CharacterReferenceRecord]:
        looks, _ = self.repository.list_looks(character_id)
        references: list[CharacterReferenceRecord] = []
        for look in looks:
            look_references, _ = self.repository.list_references(look.id)
            references.extend(look_references)
        return references

    @staticmethod
    def _select_next_default_look(
        deleting_look: CharacterLookRecord, looks: list[CharacterLookRecord]
    ) -> CharacterLookRecord | None:
        if not deleting_look.is_default:
            return None
        remaining = [look for look in looks if look.id != deleting_look.id]
        if not remaining:
            return None
        next_default = sorted(remaining, key=lambda look: (look.created_at, look.id))[0]
        next_default.is_default = True
        next_default.updated_at = utc_now()
        return next_default

    @staticmethod
    def _select_next_primary_reference(
        deleting_reference: CharacterReferenceRecord,
        references: list[CharacterReferenceRecord],
    ) -> CharacterReferenceRecord | None:
        if not deleting_reference.is_primary:
            return None
        remaining = [reference for reference in references if reference.id != deleting_reference.id]
        if not remaining:
            return None
        next_primary = sorted(
            remaining,
            key=lambda reference: (reference.created_at, reference.id),
        )[0]
        next_primary.is_primary = True
        next_primary.updated_at = utc_now()
        return next_primary

    def _character_response(self, character: CharacterRecord) -> CharacterResponse:
        looks, _ = self.repository.list_looks(character.id)
        default_look = next((look for look in looks if look.is_default), None)
        reference_count = sum(self.repository.list_references(look.id)[1] for look in looks)
        return CharacterResponse(
            id=character.id,
            project_id=character.project_id,
            name=character.name,
            aliases=character.aliases,
            role_type=RoleType(character.role_type),
            description=character.description,
            appearance_description=character.appearance_description,
            personality_description=character.personality_description,
            prompt_identity=character.prompt_identity,
            notes=character.notes,
            default_look=self._look_response(default_look) if default_look else None,
            look_count=len(looks),
            reference_count=reference_count,
            created_at=ensure_utc(character.created_at),
            updated_at=ensure_utc(character.updated_at),
        )

    def _look_response(self, look: CharacterLookRecord | None) -> CharacterLookResponse | None:
        if look is None:
            return None
        references, total = self.repository.list_references(look.id)
        primary = next((reference for reference in references if reference.is_primary), None)
        return CharacterLookResponse(
            id=look.id,
            character_id=look.character_id,
            name=look.name,
            description=look.description,
            costume_description=look.costume_description,
            hair_description=look.hair_description,
            makeup_description=look.makeup_description,
            condition_description=look.condition_description,
            prompt_appearance=look.prompt_appearance,
            is_default=look.is_default,
            reference_count=total,
            primary_reference=self._reference_response(primary) if primary else None,
            created_at=ensure_utc(look.created_at),
            updated_at=ensure_utc(look.updated_at),
        )

    def _reference_response(
        self, reference: CharacterReferenceRecord
    ) -> CharacterReferenceResponse:
        suggestions = None
        if reference.analysis_suggestions:
            suggestions = VisionAnalysisSuggestion.model_validate_json(
                reference.analysis_suggestions
            )
        return CharacterReferenceResponse(
            id=reference.id,
            look_id=reference.look_id,
            media_asset_id=reference.media_asset_id,
            shot_type=ShotType(reference.shot_type),
            view_angle=ViewAngle(reference.view_angle),
            expression=Expression(reference.expression),
            pose_type=PoseType(reference.pose_type),
            custom_expression=reference.custom_expression,
            custom_pose=reference.custom_pose,
            tags=json.loads(reference.tags or "[]"),
            description=reference.description,
            notes=reference.notes,
            is_primary=reference.is_primary,
            is_identity_anchor=reference.is_identity_anchor,
            analysis_status=AnalysisStatus(reference.analysis_status),
            suggestion_review_status=SuggestionReviewStatus(reference.suggestion_review_status),
            analysis_suggestions=suggestions,
            media_asset=self._media_asset_response(reference.media_asset),
            created_at=ensure_utc(reference.created_at),
            updated_at=ensure_utc(reference.updated_at),
        )

    @staticmethod
    def _media_asset_response(media_asset: MediaAssetRecord) -> MediaAssetResponse:
        return MediaAssetResponse(
            id=media_asset.id,
            project_id=media_asset.project_id,
            media_type=media_asset.media_type,
            original_filename=media_asset.original_filename,
            mime_type=media_asset.mime_type,
            extension=media_asset.extension,
            size_bytes=media_asset.size_bytes,
            width=media_asset.width,
            height=media_asset.height,
            sha256=media_asset.sha256,
            thumbnail_url=f"/api/media/{media_asset.id}/thumbnail",
            content_url=f"/api/media/{media_asset.id}/content",
            created_at=ensure_utc(media_asset.created_at),
        )

    @staticmethod
    def _media_asset_from_stored(
        stored: StoredImage,
        project_id: str,
        now: datetime,
    ) -> MediaAssetRecord:
        return MediaAssetRecord(
            id=str(uuid4()),
            project_id=project_id,
            media_type=MediaType.IMAGE.value,
            original_filename=stored.original_filename,
            stored_filename=stored.stored_filename,
            relative_path=stored.relative_path,
            thumbnail_relative_path=stored.thumbnail_relative_path,
            mime_type=stored.mime_type,
            extension=stored.extension,
            size_bytes=stored.size_bytes,
            width=stored.width,
            height=stored.height,
            sha256=stored.sha256,
            created_at=now,
        )

    def _delete_media_files(self, media_asset: MediaAssetRecord) -> None:
        self.storage_service.delete_relative_file(media_asset.relative_path)
        self.storage_service.delete_relative_file(media_asset.thumbnail_relative_path)

    def _delete_media_files_safely(self, media_asset: MediaAssetRecord) -> None:
        self.storage_service.delete_relative_file_safely(media_asset.relative_path)
        self.storage_service.delete_relative_file_safely(media_asset.thumbnail_relative_path)

    @staticmethod
    def _normalize_character_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                CharacterErrorCode.NAME_REQUIRED,
                CharacterErrorCode.NAME_TOO_LONG,
                100,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else CharacterErrorCode.NAME_REQUIRED
            raise_character_error(CharacterErrorCode(code), HTTP_422)

    @staticmethod
    def _normalize_look_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                CharacterErrorCode.LOOK_NAME_REQUIRED,
                CharacterErrorCode.LOOK_NAME_TOO_LONG,
                100,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else CharacterErrorCode.LOOK_NAME_REQUIRED
            raise_character_error(CharacterErrorCode(code), HTTP_422)

    @staticmethod
    def _optional(value: object, max_length: int) -> str | None:
        try:
            return normalize_optional_text(value if isinstance(value, str) else None, max_length)
        except ValueError:
            raise_character_error(CharacterErrorCode.NAME_TOO_LONG, HTTP_422)


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def raise_character_error(code: CharacterErrorCode, http_status: int) -> None:
    raise AppError(code=code.value, message=ERROR_MESSAGES[code], status_code=http_status)
