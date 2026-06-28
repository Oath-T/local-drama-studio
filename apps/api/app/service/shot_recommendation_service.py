from collections import defaultdict
from uuid import UUID

from fastapi import status

from app.api.schemas.shot_recommendation import (
    CharacterRecommendationGroup,
    CharacterReferenceRecommendationItem,
    SceneRecommendationGroup,
    SceneReferenceRecommendationItem,
    ShotRecommendationResponse,
)
from app.domain.shot import CharacterReferencePurpose, SceneReferencePurpose, ShotErrorCode
from app.domain.shot_recommendation import RecommendationReason, SceneRecommendationStatus
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)
from app.repository.shot_recommendation_repository import (
    RecommendationData,
    ShotRecommendationRepository,
)
from app.service.character_reference_ranker import CharacterReferenceRanker
from app.service.scene_reference_ranker import SceneReferenceRanker
from app.service.shot_service import ensure_utc, raise_shot_error

CHARACTER_PURPOSE_ORDER = [purpose.value for purpose in CharacterReferencePurpose]
SCENE_PURPOSE_ORDER = [purpose.value for purpose in SceneReferencePurpose]


class ShotRecommendationService:
    def __init__(
        self,
        repository: ShotRecommendationRepository,
        character_ranker: CharacterReferenceRanker | None = None,
        scene_ranker: SceneReferenceRanker | None = None,
    ) -> None:
        self.repository = repository
        self.character_ranker = character_ranker or CharacterReferenceRanker()
        self.scene_ranker = scene_ranker or SceneReferenceRanker()

    def get_recommendations(
        self,
        project_id: UUID,
        shot_id: UUID,
        limit: int,
    ) -> ShotRecommendationResponse:
        if not self.repository.project_exists(str(project_id)):
            raise_shot_error(ShotErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        shot = self.repository.get_shot(str(project_id), str(shot_id))
        if shot is None:
            raise_shot_error(ShotErrorCode.SHOT_NOT_FOUND, status.HTTP_404_NOT_FOUND)

        data = self.repository.load_recommendation_data(shot)
        return ShotRecommendationResponse(
            shot_id=shot.id,
            generated_from_updated_at=ensure_utc(shot.updated_at),
            character_recommendations=self._character_groups(data, limit),
            scene_recommendations=self._scene_group(data, limit),
        )

    def _character_groups(
        self,
        typed_data: RecommendationData,
        limit: int,
    ) -> list[CharacterRecommendationGroup]:
        references_by_character: dict[str, list[CharacterReferenceRecord]] = defaultdict(list)
        for reference in typed_data.character_references:
            if reference.media_asset is None or reference.look is None:
                continue
            references_by_character[reference.look.character_id].append(reference)

        bound_map = self._character_bound_purposes(typed_data.bound_references)
        groups: list[CharacterRecommendationGroup] = []
        for shot_character in typed_data.shot_characters:
            character = typed_data.characters.get(shot_character.character_id)
            look = typed_data.looks.get(shot_character.look_id or "")
            items = [
                self._character_item(reference, shot_character, typed_data.shot, bound_map)
                for reference in references_by_character.get(shot_character.character_id, [])
            ]
            items.sort(
                key=lambda item: (
                    -item.score,
                    not item.is_identity_anchor,
                    not item.is_primary,
                    self._character_created_at(typed_data.character_references, item.reference_id),
                    item.reference_id,
                )
            )
            groups.append(
                CharacterRecommendationGroup(
                    shot_character_id=shot_character.id,
                    character_id=shot_character.character_id,
                    character_name=character.name if character else "已删除角色",
                    look_id=shot_character.look_id,
                    look_name=look.name if look else None,
                    items=items[:limit],
                )
            )
        return groups

    def _character_item(
        self,
        reference: CharacterReferenceRecord,
        shot_character: ShotCharacterRecord,
        shot: ShotRecord,
        bound_map: dict[tuple[str, str | None], list[str]],
    ) -> CharacterReferenceRecommendationItem:
        rank = self.character_ranker.rank(shot, shot_character, reference)
        bound_purposes = bound_map.get((reference.id, shot_character.id), [])
        reasons = list(rank.reasons)
        if bound_purposes and rank.suggested_purpose.value not in bound_purposes:
            reasons.append(RecommendationReason.ALREADY_BOUND_OTHER_PURPOSE.value)
        return CharacterReferenceRecommendationItem(
            reference_id=reference.id,
            media_asset_id=reference.media_asset_id,
            thumbnail_url=f"/api/media/{reference.media_asset_id}/thumbnail",
            content_url=f"/api/media/{reference.media_asset_id}/content",
            source_look_id=reference.look_id,
            source_look_name=reference.look.name,
            shot_type=reference.shot_type,
            view_angle=reference.view_angle,
            expression=reference.expression,
            pose_type=reference.pose_type,
            is_primary=reference.is_primary,
            is_identity_anchor=reference.is_identity_anchor,
            score=rank.score,
            suggested_purpose=rank.suggested_purpose,
            reasons=stable_reason_list(reasons),
            bound_purposes=[CharacterReferencePurpose(value) for value in bound_purposes],
            is_already_bound_for_suggested_purpose=rank.suggested_purpose.value in bound_purposes,
        )

    def _scene_group(
        self,
        typed_data: RecommendationData,
        limit: int,
    ) -> SceneRecommendationGroup:
        if typed_data.shot.scene_state_id is None:
            return SceneRecommendationGroup(
                status_code=SceneRecommendationStatus.SCENE_STATE_REQUIRED,
                items=[],
            )
        if not typed_data.scene_references:
            return SceneRecommendationGroup(
                status_code=SceneRecommendationStatus.NO_REFERENCES,
                items=[],
            )
        bound_map = self._scene_bound_purposes(typed_data.bound_references)
        items = [
            self._scene_item(reference, typed_data.shot, bound_map)
            for reference in typed_data.scene_references
            if reference.media_asset is not None and reference.state is not None
        ]
        items.sort(
            key=lambda item: (
                -item.score,
                not item.is_spatial_anchor,
                not item.is_primary,
                self._scene_created_at(typed_data.scene_references, item.reference_id),
                item.reference_id,
            )
        )
        return SceneRecommendationGroup(
            status_code=SceneRecommendationStatus.READY,
            items=items[:limit],
        )

    @staticmethod
    def _character_bound_purposes(
        bound_references: list[ShotReferenceRecord],
    ) -> dict[tuple[str, str | None], list[str]]:
        result: dict[tuple[str, str | None], list[str]] = defaultdict(list)
        for reference in bound_references:
            if reference.character_reference_id is None:
                continue
            key = (reference.character_reference_id, reference.shot_character_id)
            result[key].append(reference.purpose)
        return {
            key: stable_sorted_purposes(values, CHARACTER_PURPOSE_ORDER)
            for key, values in result.items()
        }

    @staticmethod
    def _scene_bound_purposes(bound_references: list[ShotReferenceRecord]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        for reference in bound_references:
            if reference.scene_reference_id is None:
                continue
            result[reference.scene_reference_id].append(reference.purpose)
        return {
            key: stable_sorted_purposes(values, SCENE_PURPOSE_ORDER)
            for key, values in result.items()
        }

    @staticmethod
    def _character_created_at(
        references: list[CharacterReferenceRecord],
        reference_id: str,
    ) -> object:
        for reference in references:
            if reference.id == reference_id:
                return reference.created_at
        return ""

    @staticmethod
    def _scene_created_at(references: list[SceneReferenceRecord], reference_id: str) -> object:
        for reference in references:
            if reference.id == reference_id:
                return reference.created_at
        return ""

    def _scene_item(
        self,
        reference: SceneReferenceRecord,
        shot: ShotRecord,
        bound_map: dict[str, list[str]],
    ) -> SceneReferenceRecommendationItem:
        rank = self.scene_ranker.rank(shot, reference)
        bound_purposes = bound_map.get(reference.id, [])
        reasons = list(rank.reasons)
        if bound_purposes and rank.suggested_purpose.value not in bound_purposes:
            reasons.append(RecommendationReason.ALREADY_BOUND_OTHER_PURPOSE.value)
        return SceneReferenceRecommendationItem(
            reference_id=reference.id,
            media_asset_id=reference.media_asset_id,
            thumbnail_url=f"/api/media/{reference.media_asset_id}/thumbnail",
            content_url=f"/api/media/{reference.media_asset_id}/content",
            source_state_id=reference.state_id,
            source_state_name=reference.state.name,
            shot_scale=reference.shot_scale,
            camera_position=reference.camera_position,
            view_direction=reference.view_direction,
            composition_type=reference.composition_type,
            is_primary=reference.is_primary,
            is_spatial_anchor=reference.is_spatial_anchor,
            is_empty_plate=reference.is_empty_plate,
            score=rank.score,
            suggested_purpose=rank.suggested_purpose,
            reasons=stable_reason_list(reasons),
            bound_purposes=[SceneReferencePurpose(value) for value in bound_purposes],
            is_already_bound_for_suggested_purpose=rank.suggested_purpose.value in bound_purposes,
        )


def stable_sorted_purposes(values: list[str], order: list[str]) -> list[str]:
    seen = set(values)
    return [value for value in order if value in seen]


def stable_reason_list(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
