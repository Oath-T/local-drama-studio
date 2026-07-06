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
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
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
