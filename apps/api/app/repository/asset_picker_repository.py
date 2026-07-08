from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
    KeyframeGenerationTaskReferenceRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord, ShotReferenceRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class CharacterPickerData:
    character: CharacterRecord
    default_look: CharacterLookRecord | None
    cover_reference: CharacterReferenceRecord | None
    reference_count: int
    has_identity_anchor: bool
    is_selected: bool


@dataclass(frozen=True)
class ScenePickerData:
    scene: SceneRecord
    default_state: SceneStateRecord | None
    cover_reference: SceneReferenceRecord | None
    reference_count: int
    has_spatial_anchor: bool
    is_selected: bool


@dataclass(frozen=True)
class FrameImagePickerData:
    id: str
    name: str
    description: str | None
    source_label: str
    media_asset: MediaAssetRecord
    is_adopted: bool
    metadata: dict[str, str | int | bool | None]


@dataclass(frozen=True)
class CharacterLookPickerData:
    look: CharacterLookRecord
    cover_reference: CharacterReferenceRecord | None
    reference_count: int
    is_selected: bool


@dataclass(frozen=True)
class SceneStatePickerData:
    state: SceneStateRecord
    cover_reference: SceneReferenceRecord | None
    reference_count: int
    is_selected: bool


@dataclass(frozen=True)
class ReferenceImagePickerData:
    id: str
    name: str
    description: str | None
    source_kind: str
    source_label: str
    media_asset: MediaAssetRecord
    is_selected: bool
    metadata: dict[str, str | int | bool | None]


class AssetPickerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_shot(self, project_id: str, shot_id: str | None) -> ShotRecord | None:
        if not shot_id:
            return None
        return self.session.scalars(
            select(ShotRecord).where(ShotRecord.project_id == project_id, ShotRecord.id == shot_id)
        ).first()

    def list_character_options(
        self,
        project_id: str,
        *,
        shot_id: str | None,
        q: str | None,
        limit: int,
    ) -> list[CharacterPickerData]:
        statement = select(CharacterRecord).where(CharacterRecord.project_id == project_id)
        if q:
            pattern = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(CharacterRecord.name).like(pattern),
                    func.lower(CharacterRecord.description).like(pattern),
                    func.lower(CharacterRecord.aliases).like(pattern),
                )
            )
        characters = list(
            self.session.scalars(
                statement.order_by(
                    CharacterRecord.updated_at.desc(),
                    CharacterRecord.id.asc(),
                ).limit(limit)
            ).all()
        )
        character_ids = [record.id for record in characters]
        looks_by_character = self._default_looks_for_characters(character_ids)
        references_by_character = self._character_reference_summaries(character_ids)
        selected_ids = self._shot_character_ids(shot_id)

        return [
            CharacterPickerData(
                character=character,
                default_look=looks_by_character.get(character.id),
                cover_reference=references_by_character.get(character.id, {}).get("cover"),
                reference_count=int(references_by_character.get(character.id, {}).get("count", 0)),
                has_identity_anchor=bool(
                    references_by_character.get(character.id, {}).get("has_identity_anchor", False)
                ),
                is_selected=character.id in selected_ids,
            )
            for character in characters
        ]

    def list_scene_options(
        self,
        project_id: str,
        *,
        shot_id: str | None,
        q: str | None,
        limit: int,
    ) -> list[ScenePickerData]:
        statement = select(SceneRecord).where(SceneRecord.project_id == project_id)
        if q:
            pattern = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(SceneRecord.name).like(pattern),
                    func.lower(SceneRecord.description).like(pattern),
                    func.lower(SceneRecord.fixed_environment_description).like(pattern),
                )
            )
        scenes = list(
            self.session.scalars(
                statement.order_by(SceneRecord.updated_at.desc(), SceneRecord.id.asc()).limit(limit)
            ).all()
        )
        scene_ids = [record.id for record in scenes]
        states_by_scene = self._default_states_for_scenes(scene_ids)
        references_by_scene = self._scene_reference_summaries(scene_ids)
        selected_scene_id = None
        if shot_id:
            shot = self.session.get(ShotRecord, shot_id)
            selected_scene_id = shot.scene_id if shot else None

        return [
            ScenePickerData(
                scene=scene,
                default_state=states_by_scene.get(scene.id),
                cover_reference=references_by_scene.get(scene.id, {}).get("cover"),
                reference_count=int(references_by_scene.get(scene.id, {}).get("count", 0)),
                has_spatial_anchor=bool(
                    references_by_scene.get(scene.id, {}).get("has_spatial_anchor", False)
                ),
                is_selected=scene.id == selected_scene_id,
            )
            for scene in scenes
        ]

    def list_frame_image_options(
        self,
        project_id: str,
        *,
        shot_id: str,
        q: str | None,
        limit: int,
    ) -> list[FrameImagePickerData]:
        items: list[FrameImagePickerData] = []
        seen_media_ids: set[str] = set()
        pattern = q.lower() if q else None

        for item in self._video_input_frames(project_id, shot_id):
            if item.media_asset.id not in seen_media_ids and _matches_frame_query(item, pattern):
                items.append(item)
                seen_media_ids.add(item.media_asset.id)
            if len(items) >= limit:
                return items

        for item in self._selected_keyframe_outputs(project_id, shot_id):
            if item.media_asset.id not in seen_media_ids and _matches_frame_query(item, pattern):
                items.append(item)
                seen_media_ids.add(item.media_asset.id)
            if len(items) >= limit:
                return items

        for item in self._shot_reference_frames(project_id, shot_id):
            if item.media_asset.id not in seen_media_ids and _matches_frame_query(item, pattern):
                items.append(item)
                seen_media_ids.add(item.media_asset.id)
            if len(items) >= limit:
                return items
        return items

    def character_exists(self, project_id: str, character_id: str) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(CharacterRecord)
                .where(
                    CharacterRecord.project_id == project_id,
                    CharacterRecord.id == character_id,
                )
            )
            or 0
        ) > 0

    def scene_exists(self, project_id: str, scene_id: str) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(SceneRecord)
                .where(SceneRecord.project_id == project_id, SceneRecord.id == scene_id)
            )
            or 0
        ) > 0

    def list_character_look_options(
        self,
        project_id: str,
        *,
        character_id: str,
        shot_character_id: str | None,
        q: str | None,
        limit: int,
    ) -> list[CharacterLookPickerData]:
        statement = (
            select(CharacterLookRecord)
            .join(CharacterRecord, CharacterRecord.id == CharacterLookRecord.character_id)
            .where(
                CharacterRecord.project_id == project_id,
                CharacterLookRecord.character_id == character_id,
            )
        )
        if q:
            pattern = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(CharacterLookRecord.name).like(pattern),
                    func.lower(CharacterLookRecord.description).like(pattern),
                    func.lower(CharacterLookRecord.costume_description).like(pattern),
                    func.lower(CharacterLookRecord.prompt_appearance).like(pattern),
                )
            )
        looks = list(
            self.session.scalars(
                statement.order_by(
                    CharacterLookRecord.is_default.desc(),
                    CharacterLookRecord.created_at.asc(),
                    CharacterLookRecord.id.asc(),
                ).limit(limit)
            ).all()
        )
        look_ids = [look.id for look in looks]
        references_by_look = self._character_reference_summaries_by_look(look_ids)
        selected_look_id = None
        if shot_character_id:
            shot_character = self.session.get(ShotCharacterRecord, shot_character_id)
            selected_look_id = (
                shot_character.look_id
                if shot_character and shot_character.character_id == character_id
                else None
            )
        return [
            CharacterLookPickerData(
                look=look,
                cover_reference=references_by_look.get(look.id, {}).get("cover"),
                reference_count=int(references_by_look.get(look.id, {}).get("count", 0)),
                is_selected=look.id == selected_look_id,
            )
            for look in looks
        ]

    def list_scene_state_options(
        self,
        project_id: str,
        *,
        scene_id: str,
        shot_id: str | None,
        q: str | None,
        limit: int,
    ) -> list[SceneStatePickerData]:
        statement = (
            select(SceneStateRecord)
            .join(SceneRecord, SceneRecord.id == SceneStateRecord.scene_id)
            .where(SceneRecord.project_id == project_id, SceneStateRecord.scene_id == scene_id)
        )
        if q:
            pattern = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(SceneStateRecord.name).like(pattern),
                    func.lower(SceneStateRecord.description).like(pattern),
                    func.lower(SceneStateRecord.environment_condition).like(pattern),
                    func.lower(SceneStateRecord.prompt_state).like(pattern),
                )
            )
        states = list(
            self.session.scalars(
                statement.order_by(
                    SceneStateRecord.is_default.desc(),
                    SceneStateRecord.created_at.asc(),
                    SceneStateRecord.id.asc(),
                ).limit(limit)
            ).all()
        )
        state_ids = [state.id for state in states]
        references_by_state = self._scene_reference_summaries_by_state(state_ids)
        selected_state_id = None
        if shot_id:
            shot = self.session.get(ShotRecord, shot_id)
            selected_state_id = shot.scene_state_id if shot and shot.scene_id == scene_id else None
        return [
            SceneStatePickerData(
                state=state,
                cover_reference=references_by_state.get(state.id, {}).get("cover"),
                reference_count=int(references_by_state.get(state.id, {}).get("count", 0)),
                is_selected=state.id == selected_state_id,
            )
            for state in states
        ]

    def list_reference_image_options(
        self,
        project_id: str,
        *,
        shot_id: str,
        task_id: str | None,
        q: str | None,
        limit: int,
    ) -> list[ReferenceImagePickerData]:
        items: list[ReferenceImagePickerData] = []
        seen_keys: set[str] = set()
        task_reference_ids = self._keyframe_task_shot_reference_ids(project_id, shot_id, task_id)
        pattern = q.lower() if q else None

        for item in self._shot_reference_image_options(project_id, shot_id, task_reference_ids):
            item_keys = _reference_seen_keys(item)
            if seen_keys.isdisjoint(item_keys) and _matches_reference_query(item, pattern):
                items.append(item)
                seen_keys.update(item_keys)
            if len(items) >= limit:
                return items

        for item in self._shot_character_reference_image_options(project_id, shot_id):
            item_keys = _reference_seen_keys(item)
            if seen_keys.isdisjoint(item_keys) and _matches_reference_query(item, pattern):
                items.append(item)
                seen_keys.update(item_keys)
            if len(items) >= limit:
                return items

        for item in self._shot_scene_reference_image_options(project_id, shot_id):
            item_keys = _reference_seen_keys(item)
            if seen_keys.isdisjoint(item_keys) and _matches_reference_query(item, pattern):
                items.append(item)
                seen_keys.update(item_keys)
            if len(items) >= limit:
                return items
        return items

    def _default_looks_for_characters(
        self, character_ids: list[str]
    ) -> dict[str, CharacterLookRecord]:
        if not character_ids:
            return {}
        looks = list(
            self.session.scalars(
                select(CharacterLookRecord)
                .where(CharacterLookRecord.character_id.in_(character_ids))
                .order_by(
                    CharacterLookRecord.character_id.asc(),
                    CharacterLookRecord.is_default.desc(),
                    CharacterLookRecord.created_at.asc(),
                    CharacterLookRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, CharacterLookRecord] = {}
        for look in looks:
            result.setdefault(look.character_id, look)
        return result

    def _default_states_for_scenes(self, scene_ids: list[str]) -> dict[str, SceneStateRecord]:
        if not scene_ids:
            return {}
        states = list(
            self.session.scalars(
                select(SceneStateRecord)
                .where(SceneStateRecord.scene_id.in_(scene_ids))
                .order_by(
                    SceneStateRecord.scene_id.asc(),
                    SceneStateRecord.is_default.desc(),
                    SceneStateRecord.created_at.asc(),
                    SceneStateRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, SceneStateRecord] = {}
        for state in states:
            result.setdefault(state.scene_id, state)
        return result

    def _character_reference_summaries(
        self, character_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        if not character_ids:
            return {}
        references = list(
            self.session.scalars(
                select(CharacterReferenceRecord)
                .join(
                    CharacterLookRecord,
                    CharacterLookRecord.id == CharacterReferenceRecord.look_id,
                )
                .where(CharacterLookRecord.character_id.in_(character_ids))
                .options(
                    joinedload(CharacterReferenceRecord.media_asset),
                    joinedload(CharacterReferenceRecord.look),
                )
                .order_by(
                    CharacterLookRecord.character_id.asc(),
                    CharacterReferenceRecord.is_identity_anchor.desc(),
                    CharacterReferenceRecord.is_primary.desc(),
                    CharacterReferenceRecord.created_at.asc(),
                    CharacterReferenceRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, dict[str, object]] = {}
        for reference in references:
            character_id = reference.look.character_id
            summary = result.setdefault(
                character_id,
                {"cover": reference, "count": 0, "has_identity_anchor": False},
            )
            summary["count"] = int(summary["count"]) + 1
            summary["has_identity_anchor"] = bool(summary["has_identity_anchor"]) or bool(
                reference.is_identity_anchor
            )
        return result

    def _scene_reference_summaries(self, scene_ids: list[str]) -> dict[str, dict[str, object]]:
        if not scene_ids:
            return {}
        references = list(
            self.session.scalars(
                select(SceneReferenceRecord)
                .join(SceneStateRecord, SceneStateRecord.id == SceneReferenceRecord.state_id)
                .where(SceneStateRecord.scene_id.in_(scene_ids))
                .options(
                    joinedload(SceneReferenceRecord.media_asset),
                    joinedload(SceneReferenceRecord.state),
                )
                .order_by(
                    SceneStateRecord.scene_id.asc(),
                    SceneReferenceRecord.is_spatial_anchor.desc(),
                    SceneReferenceRecord.is_primary.desc(),
                    SceneReferenceRecord.created_at.asc(),
                    SceneReferenceRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, dict[str, object]] = {}
        for reference in references:
            scene_id = reference.state.scene_id
            summary = result.setdefault(
                scene_id,
                {"cover": reference, "count": 0, "has_spatial_anchor": False},
            )
            summary["count"] = int(summary["count"]) + 1
            summary["has_spatial_anchor"] = bool(summary["has_spatial_anchor"]) or bool(
                reference.is_spatial_anchor
            )
        return result

    def _character_reference_summaries_by_look(
        self, look_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        if not look_ids:
            return {}
        references = list(
            self.session.scalars(
                select(CharacterReferenceRecord)
                .where(CharacterReferenceRecord.look_id.in_(look_ids))
                .options(joinedload(CharacterReferenceRecord.media_asset))
                .order_by(
                    CharacterReferenceRecord.look_id.asc(),
                    CharacterReferenceRecord.is_primary.desc(),
                    CharacterReferenceRecord.is_identity_anchor.desc(),
                    CharacterReferenceRecord.created_at.asc(),
                    CharacterReferenceRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, dict[str, object]] = {}
        for reference in references:
            summary = result.setdefault(reference.look_id, {"cover": reference, "count": 0})
            summary["count"] = int(summary["count"]) + 1
        return result

    def _scene_reference_summaries_by_state(
        self, state_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        if not state_ids:
            return {}
        references = list(
            self.session.scalars(
                select(SceneReferenceRecord)
                .where(SceneReferenceRecord.state_id.in_(state_ids))
                .options(joinedload(SceneReferenceRecord.media_asset))
                .order_by(
                    SceneReferenceRecord.state_id.asc(),
                    SceneReferenceRecord.is_primary.desc(),
                    SceneReferenceRecord.is_spatial_anchor.desc(),
                    SceneReferenceRecord.created_at.asc(),
                    SceneReferenceRecord.id.asc(),
                )
            ).all()
        )
        result: dict[str, dict[str, object]] = {}
        for reference in references:
            summary = result.setdefault(reference.state_id, {"cover": reference, "count": 0})
            summary["count"] = int(summary["count"]) + 1
        return result

    def _shot_character_ids(self, shot_id: str | None) -> set[str]:
        if not shot_id:
            return set()
        return set(
            self.session.scalars(
                select(ShotCharacterRecord.character_id).where(
                    ShotCharacterRecord.shot_id == shot_id
                )
            ).all()
        )

    def _video_input_frames(self, project_id: str, shot_id: str) -> list[FrameImagePickerData]:
        rows = self.session.execute(
            select(VideoGenerationTaskInputRecord, MediaAssetRecord)
            .join(
                VideoGenerationTaskRecord,
                VideoGenerationTaskRecord.id == VideoGenerationTaskInputRecord.task_id,
            )
            .join(
                MediaAssetRecord,
                MediaAssetRecord.id == VideoGenerationTaskInputRecord.media_asset_id,
            )
            .where(
                VideoGenerationTaskRecord.project_id == project_id,
                VideoGenerationTaskRecord.shot_id == shot_id,
                MediaAssetRecord.media_type == "image",
            )
            .order_by(
                VideoGenerationTaskInputRecord.role.asc(),
                VideoGenerationTaskInputRecord.updated_at.desc(),
                VideoGenerationTaskInputRecord.id.asc(),
            )
        ).all()
        items: list[FrameImagePickerData] = []
        for task_input, media in rows:
            role_label = "已选首帧" if task_input.role == "start_frame" else "已选尾帧"
            items.append(
                FrameImagePickerData(
                    id=media.id,
                    name=media.original_filename,
                    description=role_label,
                    source_label=role_label,
                    media_asset=media,
                    is_adopted=True,
                    metadata={"role": task_input.role, "media_asset_id": media.id},
                )
            )
        return items

    def _keyframe_task_shot_reference_ids(
        self, project_id: str, shot_id: str, task_id: str | None
    ) -> set[str] | None:
        if task_id is None:
            return None
        task = self.session.scalars(
            select(KeyframeGenerationTaskRecord).where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
                KeyframeGenerationTaskRecord.id == task_id,
            )
        ).first()
        if task is None:
            return set()
        return set(
            self.session.scalars(
                select(KeyframeGenerationTaskReferenceRecord.shot_reference_id).where(
                    KeyframeGenerationTaskReferenceRecord.task_id == task_id,
                    KeyframeGenerationTaskReferenceRecord.shot_reference_id.is_not(None),
                )
            ).all()
        )

    def _shot_reference_image_options(
        self,
        project_id: str,
        shot_id: str,
        task_reference_ids: set[str] | None,
    ) -> list[ReferenceImagePickerData]:
        rows = self.session.execute(
            select(ShotReferenceRecord, CharacterReferenceRecord, SceneReferenceRecord)
            .outerjoin(
                CharacterReferenceRecord,
                CharacterReferenceRecord.id == ShotReferenceRecord.character_reference_id,
            )
            .outerjoin(
                SceneReferenceRecord,
                SceneReferenceRecord.id == ShotReferenceRecord.scene_reference_id,
            )
            .where(ShotReferenceRecord.shot_id == shot_id)
            .order_by(ShotReferenceRecord.order_index.asc(), ShotReferenceRecord.id.asc())
        ).all()
        media_ids = sorted(
            {
                reference.media_asset_id
                for _, character_reference, scene_reference in rows
                for reference in [character_reference or scene_reference]
                if reference is not None
            }
        )
        media_by_id = self._media_assets_by_id(project_id, media_ids)
        items: list[ReferenceImagePickerData] = []
        for shot_reference, character_reference, scene_reference in rows:
            source_reference = character_reference or scene_reference
            if source_reference is None:
                continue
            media = media_by_id.get(source_reference.media_asset_id)
            if media is None:
                continue
            is_character = shot_reference.reference_type == "character"
            items.append(
                ReferenceImagePickerData(
                    id=shot_reference.id,
                    name=media.original_filename,
                    description=source_reference.description,
                    source_kind="shot_reference",
                    source_label="镜头参考图",
                    media_asset=media,
                    is_selected=(
                        shot_reference.id in task_reference_ids
                        if task_reference_ids is not None
                        else True
                    ),
                    metadata={
                        "reference_type": shot_reference.reference_type,
                        "shot_reference_id": shot_reference.id,
                        "character_reference_id": shot_reference.character_reference_id,
                        "scene_reference_id": shot_reference.scene_reference_id,
                        "shot_character_id": shot_reference.shot_character_id,
                        "purpose": shot_reference.purpose,
                        "suggested_purpose": shot_reference.purpose,
                        "is_bound_to_shot": True,
                        "is_added_to_task": (
                            shot_reference.id in task_reference_ids
                            if task_reference_ids is not None
                            else False
                        ),
                        "source_reference_id": (
                            shot_reference.character_reference_id
                            if is_character
                            else shot_reference.scene_reference_id
                        ),
                    },
                )
            )
        return items

    def _shot_character_reference_image_options(
        self, project_id: str, shot_id: str
    ) -> list[ReferenceImagePickerData]:
        shot_characters = list(
            self.session.scalars(
                select(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id == shot_id)
                .order_by(ShotCharacterRecord.order_index.asc(), ShotCharacterRecord.id.asc())
            ).all()
        )
        if not shot_characters:
            return []
        character_ids = sorted({item.character_id for item in shot_characters})
        references = list(
            self.session.scalars(
                select(CharacterReferenceRecord)
                .join(
                    CharacterLookRecord,
                    CharacterLookRecord.id == CharacterReferenceRecord.look_id,
                )
                .where(CharacterLookRecord.character_id.in_(character_ids))
                .options(
                    joinedload(CharacterReferenceRecord.media_asset),
                    joinedload(CharacterReferenceRecord.look),
                )
                .order_by(
                    CharacterLookRecord.character_id.asc(),
                    CharacterReferenceRecord.is_identity_anchor.desc(),
                    CharacterReferenceRecord.is_primary.desc(),
                    CharacterReferenceRecord.created_at.asc(),
                    CharacterReferenceRecord.id.asc(),
                )
            ).all()
        )
        shot_characters_by_character: dict[str, list[ShotCharacterRecord]] = {}
        for shot_character in shot_characters:
            shot_characters_by_character.setdefault(shot_character.character_id, []).append(
                shot_character
            )
        items: list[ReferenceImagePickerData] = []
        for reference in references:
            matching_shot_character = _matching_shot_character(
                reference, shot_characters_by_character.get(reference.look.character_id, [])
            )
            if matching_shot_character is None:
                continue
            media = reference.media_asset
            if media is None or media.project_id != project_id or media.media_type != "image":
                continue
            suggested_purpose = "identity" if reference.is_identity_anchor else "appearance"
            badges = []
            if reference.is_identity_anchor:
                badges.append("身份基准图")
            if reference.is_primary:
                badges.append("主图")
            items.append(
                ReferenceImagePickerData(
                    id=reference.id,
                    name=media.original_filename,
                    description=reference.description,
                    source_kind="character_reference",
                    source_label="人物参考图",
                    media_asset=media,
                    is_selected=False,
                    metadata={
                        "reference_type": "character",
                        "character_reference_id": reference.id,
                        "scene_reference_id": None,
                        "shot_reference_id": None,
                        "shot_character_id": matching_shot_character.id,
                        "purpose": suggested_purpose,
                        "suggested_purpose": suggested_purpose,
                        "is_bound_to_shot": False,
                        "is_added_to_task": False,
                        "source_reference_id": reference.id,
                        "source_badges": ",".join(badges),
                    },
                )
            )
        return items

    def _shot_scene_reference_image_options(
        self, project_id: str, shot_id: str
    ) -> list[ReferenceImagePickerData]:
        shot = self.session.get(ShotRecord, shot_id)
        if shot is None or shot.project_id != project_id or shot.scene_state_id is None:
            return []
        references = list(
            self.session.scalars(
                select(SceneReferenceRecord)
                .where(SceneReferenceRecord.state_id == shot.scene_state_id)
                .options(joinedload(SceneReferenceRecord.media_asset))
                .order_by(
                    SceneReferenceRecord.is_spatial_anchor.desc(),
                    SceneReferenceRecord.is_primary.desc(),
                    SceneReferenceRecord.created_at.asc(),
                    SceneReferenceRecord.id.asc(),
                )
            ).all()
        )
        items: list[ReferenceImagePickerData] = []
        for reference in references:
            media = reference.media_asset
            if media is None or media.project_id != project_id or media.media_type != "image":
                continue
            suggested_purpose = "spatial" if reference.is_spatial_anchor else "environment"
            badges = []
            if reference.is_spatial_anchor:
                badges.append("空间结构参考图")
            if reference.is_empty_plate:
                badges.append("空镜")
            if reference.is_primary:
                badges.append("主图")
            items.append(
                ReferenceImagePickerData(
                    id=reference.id,
                    name=media.original_filename,
                    description=reference.description,
                    source_kind="scene_reference",
                    source_label="场景参考图",
                    media_asset=media,
                    is_selected=False,
                    metadata={
                        "reference_type": "scene",
                        "character_reference_id": None,
                        "scene_reference_id": reference.id,
                        "shot_reference_id": None,
                        "shot_character_id": None,
                        "purpose": suggested_purpose,
                        "suggested_purpose": suggested_purpose,
                        "is_bound_to_shot": False,
                        "is_added_to_task": False,
                        "source_reference_id": reference.id,
                        "source_badges": ",".join(badges),
                    },
                )
            )
        return items

    def _media_assets_by_id(
        self, project_id: str, media_ids: list[str]
    ) -> dict[str, MediaAssetRecord]:
        if not media_ids:
            return {}
        return {
            media.id: media
            for media in self.session.scalars(
                select(MediaAssetRecord).where(
                    MediaAssetRecord.project_id == project_id,
                    MediaAssetRecord.id.in_(media_ids),
                    MediaAssetRecord.media_type == "image",
                )
            ).all()
        }

    def _selected_keyframe_outputs(
        self, project_id: str, shot_id: str
    ) -> list[FrameImagePickerData]:
        rows = self.session.execute(
            select(
                KeyframeGenerationOutputRecord,
                KeyframeGenerationTaskRecord,
                MediaAssetRecord,
            )
            .join(
                KeyframeGenerationRunRecord,
                KeyframeGenerationRunRecord.id == KeyframeGenerationOutputRecord.run_id,
            )
            .join(
                KeyframeGenerationTaskRecord,
                KeyframeGenerationTaskRecord.id == KeyframeGenerationRunRecord.keyframe_task_id,
            )
            .join(
                MediaAssetRecord,
                MediaAssetRecord.id == KeyframeGenerationOutputRecord.media_asset_id,
            )
            .where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
                MediaAssetRecord.media_type == "image",
            )
            .order_by(
                KeyframeGenerationOutputRecord.is_selected.desc(),
                KeyframeGenerationOutputRecord.created_at.desc(),
                KeyframeGenerationOutputRecord.id.asc(),
            )
        ).all()
        items: list[FrameImagePickerData] = []
        for output, task, media in rows:
            source_label = "已采用关键帧" if output.is_selected else "关键帧输出"
            items.append(
                FrameImagePickerData(
                    id=media.id,
                    name=media.original_filename,
                    description=task.name,
                    source_label=source_label,
                    media_asset=media,
                    is_adopted=output.is_selected,
                    metadata={
                        "keyframe_output_id": output.id,
                        "keyframe_task_id": task.id,
                        "output_index": output.output_index,
                    },
                )
            )
        return items

    def _shot_reference_frames(self, project_id: str, shot_id: str) -> list[FrameImagePickerData]:
        rows = self.session.execute(
            select(ShotReferenceRecord, CharacterReferenceRecord, SceneReferenceRecord)
            .outerjoin(
                CharacterReferenceRecord,
                CharacterReferenceRecord.id == ShotReferenceRecord.character_reference_id,
            )
            .outerjoin(
                SceneReferenceRecord,
                SceneReferenceRecord.id == ShotReferenceRecord.scene_reference_id,
            )
            .where(ShotReferenceRecord.shot_id == shot_id)
            .order_by(ShotReferenceRecord.order_index.asc(), ShotReferenceRecord.id.asc())
        ).all()
        media_ids = sorted(
            {
                reference.media_asset_id
                for _, character_reference, scene_reference in rows
                for reference in [character_reference or scene_reference]
                if reference is not None
            }
        )
        media_by_id = {
            media.id: media
            for media in self.session.scalars(
                select(MediaAssetRecord).where(
                    MediaAssetRecord.project_id == project_id,
                    MediaAssetRecord.id.in_(media_ids),
                    MediaAssetRecord.media_type == "image",
                )
            ).all()
        }
        items: list[FrameImagePickerData] = []
        for shot_reference, character_reference, scene_reference in rows:
            source_reference = character_reference or scene_reference
            if source_reference is None:
                continue
            media = media_by_id.get(source_reference.media_asset_id)
            if media is None:
                continue
            label = (
                "镜头人物参考图"
                if shot_reference.reference_type == "character"
                else "镜头场景参考图"
            )
            items.append(
                FrameImagePickerData(
                    id=media.id,
                    name=media.original_filename,
                    description=source_reference.description,
                    source_label=label,
                    media_asset=media,
                    is_adopted=False,
                    metadata={
                        "shot_reference_id": shot_reference.id,
                        "reference_type": shot_reference.reference_type,
                        "purpose": shot_reference.purpose,
                    },
                )
            )
        return items


def _matches_frame_query(item: FrameImagePickerData, pattern: str | None) -> bool:
    if not pattern:
        return True
    haystack = " ".join(
        value.lower()
        for value in [item.name, item.description, item.source_label]
        if isinstance(value, str)
    )
    return pattern in haystack


def _matches_reference_query(item: ReferenceImagePickerData, pattern: str | None) -> bool:
    if not pattern:
        return True
    haystack = " ".join(
        value.lower()
        for value in [
            item.name,
            item.description,
            item.source_label,
            str(item.metadata.get("purpose") or ""),
        ]
        if isinstance(value, str)
    )
    return pattern in haystack


def _reference_seen_keys(item: ReferenceImagePickerData) -> set[str]:
    keys = {item.id}
    reference_type = item.metadata.get("reference_type")
    character_reference_id = item.metadata.get("character_reference_id")
    scene_reference_id = item.metadata.get("scene_reference_id")
    if reference_type == "character" and isinstance(character_reference_id, str):
        keys.add(f"character:{character_reference_id}")
    if reference_type == "scene" and isinstance(scene_reference_id, str):
        keys.add(f"scene:{scene_reference_id}")
    return keys


def _matching_shot_character(
    reference: CharacterReferenceRecord,
    shot_characters: list[ShotCharacterRecord],
) -> ShotCharacterRecord | None:
    for shot_character in shot_characters:
        if shot_character.look_id and shot_character.look_id == reference.look_id:
            return shot_character
    for shot_character in shot_characters:
        if shot_character.look_id is None:
            return shot_character
    return None
