from app.api.schemas.keyframe_task import (
    KeyframeShotSnapshot,
    KeyframeShotSnapshotCharacter,
)
from app.infrastructure.models.shot import ShotRecord
from app.repository.keyframe_task_repository import KeyframeTaskRepository


class KeyframeTaskSnapshotBuilder:
    def __init__(self, repository: KeyframeTaskRepository) -> None:
        self.repository = repository

    def build(self, shot: ShotRecord) -> KeyframeShotSnapshot:
        shot_characters = self.repository.list_shot_characters(shot.id)
        characters = self.repository.get_characters_by_ids(
            [shot_character.character_id for shot_character in shot_characters]
        )
        looks = self.repository.get_looks_by_ids(
            [shot_character.look_id for shot_character in shot_characters if shot_character.look_id]
        )
        scene = self.repository.get_scene_by_id(shot.scene_id)
        state = self.repository.get_state_by_id(shot.scene_state_id)
        return KeyframeShotSnapshot(
            schema_version=1,
            shot_id=shot.id,
            order_index=shot.order_index,
            title=shot.name,
            story_description=shot.story_description,
            visual_description=shot.visual_description,
            action_summary=shot.action_summary,
            dialogue=shot.dialogue,
            mood_description=shot.mood_description,
            duration_seconds=shot.duration_seconds,
            shot_scale=shot.shot_scale,
            camera_angle=shot.camera_angle,
            custom_camera_angle=shot.custom_camera_angle,
            camera_height=shot.camera_height,
            custom_camera_height=shot.custom_camera_height,
            lens=None,
            composition_type=shot.composition_type,
            custom_composition=shot.custom_composition,
            camera_movement=shot.camera_movement,
            custom_camera_movement=shot.custom_camera_movement,
            scene_id=shot.scene_id,
            scene_name=scene.name if scene else None,
            scene_state_id=shot.scene_state_id,
            scene_state_name=state.name if state else None,
            characters=[
                KeyframeShotSnapshotCharacter(
                    shot_character_id=shot_character.id,
                    character_id=shot_character.character_id,
                    character_name=characters.get(shot_character.character_id).name
                    if characters.get(shot_character.character_id)
                    else "已删除角色",
                    look_id=shot_character.look_id,
                    look_name=looks.get(shot_character.look_id).name
                    if shot_character.look_id and looks.get(shot_character.look_id)
                    else None,
                    action_description=shot_character.action_description,
                    expression_description=shot_character.expression_description,
                    position_description=shot_character.position_description,
                    is_primary_subject=shot_character.is_primary_subject,
                    order_index=shot_character.order_index,
                )
                for shot_character in shot_characters
            ],
        )
