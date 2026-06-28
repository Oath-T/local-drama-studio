from dataclasses import dataclass

from app.domain.scene import (
    CameraPosition,
    CompositionType,
    ViewDirection,
)
from app.domain.scene import (
    ShotScale as SceneShotScale,
)
from app.domain.shot import CameraHeight, SceneReferencePurpose, ShotCompositionType, ShotScale
from app.domain.shot_recommendation import (
    KEYWORD_DICTIONARY,
    RecommendationReason,
    normalize_recommendation_text,
    stable_unique,
    text_matches_keywords,
)
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import ShotRecord


@dataclass(frozen=True)
class SceneRankResult:
    score: int
    suggested_purpose: SceneReferencePurpose
    reasons: list[str]


SCENE_SCALE_GROUPS: dict[str, set[str]] = {
    "wide": {
        ShotScale.EXTREME_WIDE.value,
        ShotScale.WIDE.value,
        SceneShotScale.EXTREME_WIDE.value,
        SceneShotScale.WIDE.value,
    },
    "medium": {
        ShotScale.FULL.value,
        ShotScale.MEDIUM_WIDE.value,
        ShotScale.MEDIUM.value,
        SceneShotScale.FULL.value,
        SceneShotScale.MEDIUM_WIDE.value,
        SceneShotScale.MEDIUM.value,
    },
    "close": {
        ShotScale.MEDIUM_CLOSE.value,
        ShotScale.CLOSE.value,
        ShotScale.CLOSE_UP.value,
        ShotScale.EXTREME_CLOSE_UP.value,
        SceneShotScale.CLOSE.value,
        SceneShotScale.DETAIL.value,
    },
}

CAMERA_POSITION_EXACT: dict[str, set[str]] = {
    CameraHeight.EYE_LEVEL.value: {CameraPosition.EYE_LEVEL.value},
    CameraHeight.LOW.value: {CameraPosition.LOW_ANGLE.value},
    CameraHeight.HIGH.value: {CameraPosition.HIGH_ANGLE.value},
    CameraHeight.GROUND.value: {CameraPosition.GROUND_LEVEL.value},
    CameraHeight.OVERHEAD.value: {CameraPosition.OVERHEAD.value},
    CameraHeight.AERIAL.value: {CameraPosition.AERIAL.value},
}

CAMERA_POSITION_CLOSE: dict[str, set[str]] = {
    CameraHeight.LOW.value: {CameraPosition.GROUND_LEVEL.value},
    CameraHeight.HIGH.value: {CameraPosition.OVERHEAD.value},
    CameraHeight.OVERHEAD.value: {CameraPosition.HIGH_ANGLE.value, CameraPosition.AERIAL.value},
}

VIEW_DIRECTION_EXACT: dict[str, set[str]] = {
    "front": {ViewDirection.FRONT.value},
    "back": {ViewDirection.BACK.value},
    "left_profile": {ViewDirection.LEFT.value},
    "right_profile": {ViewDirection.RIGHT.value},
    "left_three_quarter": {ViewDirection.DIAGONAL_LEFT.value},
    "right_three_quarter": {ViewDirection.DIAGONAL_RIGHT.value},
}

VIEW_DIRECTION_CLOSE: dict[str, set[str]] = {
    "front": {ViewDirection.DIAGONAL_LEFT.value, ViewDirection.DIAGONAL_RIGHT.value},
    "left_profile": {ViewDirection.DIAGONAL_LEFT.value},
    "right_profile": {ViewDirection.DIAGONAL_RIGHT.value},
    "left_three_quarter": {ViewDirection.LEFT.value, ViewDirection.FRONT.value},
    "right_three_quarter": {ViewDirection.RIGHT.value, ViewDirection.FRONT.value},
}

COMPOSITION_EXACT: dict[str, set[str]] = {
    ShotCompositionType.CENTERED.value: {CompositionType.CENTERED.value},
    ShotCompositionType.SYMMETRICAL.value: {CompositionType.SYMMETRICAL.value},
    ShotCompositionType.RULE_OF_THIRDS.value: {CompositionType.RULE_OF_THIRDS.value},
    ShotCompositionType.LEADING_LINES.value: {CompositionType.LEADING_LINES.value},
    ShotCompositionType.FRAME_WITHIN_FRAME.value: {CompositionType.FRAME_WITHIN_FRAME.value},
    ShotCompositionType.LAYERED.value: {CompositionType.LAYERED.value},
}


class SceneReferenceRanker:
    def rank(self, shot: ShotRecord, reference: SceneReferenceRecord) -> SceneRankResult:
        score = 0
        reasons: list[str] = []
        applied: set[RecommendationReason] = set()

        scale_match = self._score_shot_scale(shot.shot_scale, reference.shot_scale)
        if scale_match == "exact":
            score += self._add_reason(applied, reasons, RecommendationReason.SHOT_SCALE_EXACT, 25)
        elif scale_match == "close":
            score += self._add_reason(applied, reasons, RecommendationReason.SHOT_SCALE_CLOSE, 15)

        position_match = self._score_camera_position(shot.camera_height, reference.camera_position)
        if position_match == "exact":
            score += self._add_reason(
                applied, reasons, RecommendationReason.CAMERA_POSITION_EXACT, 20
            )
        elif position_match == "close":
            score += self._add_reason(
                applied, reasons, RecommendationReason.CAMERA_POSITION_CLOSE, 10
            )

        direction_match = self._score_view_direction(shot.camera_angle, reference.view_direction)
        if direction_match == "exact":
            score += self._add_reason(
                applied, reasons, RecommendationReason.VIEW_DIRECTION_EXACT, 15
            )
        elif direction_match == "close":
            score += self._add_reason(
                applied, reasons, RecommendationReason.VIEW_DIRECTION_CLOSE, 8
            )

        composition_match = self._score_composition(
            shot.composition_type, reference.composition_type
        )
        if composition_match:
            score += self._add_reason(applied, reasons, RecommendationReason.COMPOSITION_EXACT, 15)

        if reference.is_spatial_anchor:
            score += self._add_reason(applied, reasons, RecommendationReason.SPATIAL_ANCHOR, 10)
        if reference.is_primary:
            score += self._add_reason(applied, reasons, RecommendationReason.PRIMARY_REFERENCE, 5)
        if reference.is_empty_plate:
            score += self._add_reason(applied, reasons, RecommendationReason.EMPTY_PLATE, 5)

        lighting_match = self._matches_lighting_keywords(shot, reference)
        if lighting_match:
            score += self._add_reason(applied, reasons, RecommendationReason.KEYWORD_MATCH, 10)

        purpose = self._suggest_purpose(
            reference=reference,
            scale_match=scale_match,
            position_match=position_match,
            direction_match=direction_match,
            composition_match=composition_match,
            lighting_match=lighting_match,
        )
        return SceneRankResult(
            score=min(score, 100),
            suggested_purpose=purpose,
            reasons=stable_unique(reasons),
        )

    @staticmethod
    def _add_reason(
        applied: set[RecommendationReason],
        reasons: list[str],
        reason: RecommendationReason,
        score: int,
    ) -> int:
        if reason in applied:
            return 0
        applied.add(reason)
        reasons.append(reason.value)
        return score

    @staticmethod
    def _score_shot_scale(shot_scale: str, scene_scale: str) -> str | None:
        if shot_scale == ShotScale.UNKNOWN.value or scene_scale == SceneShotScale.UNKNOWN.value:
            return None
        if shot_scale == scene_scale:
            return "exact"
        shot_group = next(
            (group for group, values in SCENE_SCALE_GROUPS.items() if shot_scale in values),
            None,
        )
        scene_group = next(
            (group for group, values in SCENE_SCALE_GROUPS.items() if scene_scale in values),
            None,
        )
        return "close" if shot_group and shot_group == scene_group else None

    @staticmethod
    def _score_camera_position(camera_height: str, camera_position: str) -> str | None:
        if camera_position in CAMERA_POSITION_EXACT.get(camera_height, set()):
            return "exact"
        if camera_position in CAMERA_POSITION_CLOSE.get(camera_height, set()):
            return "close"
        return None

    @staticmethod
    def _score_view_direction(camera_angle: str, view_direction: str) -> str | None:
        if view_direction in VIEW_DIRECTION_EXACT.get(camera_angle, set()):
            return "exact"
        if view_direction in VIEW_DIRECTION_CLOSE.get(camera_angle, set()):
            return "close"
        return None

    @staticmethod
    def _score_composition(shot_composition: str, scene_composition: str) -> bool:
        return scene_composition in COMPOSITION_EXACT.get(shot_composition, set())

    @staticmethod
    def _matches_lighting_keywords(shot: ShotRecord, reference: SceneReferenceRecord) -> bool:
        shot_text = normalize_recommendation_text(
            [
                shot.visual_description,
                shot.story_description,
                shot.mood_description,
                shot.action_summary,
            ]
        )
        candidate_text = normalize_recommendation_text(
            [
                " ".join(SceneReferenceRanker._safe_tags(reference.tags)),
                reference.description,
            ]
        )
        return any(
            text_matches_keywords(shot_text, keywords)
            and text_matches_keywords(candidate_text, keywords)
            for keywords in KEYWORD_DICTIONARY["lighting"].values()
        )

    @staticmethod
    def _suggest_purpose(
        reference: SceneReferenceRecord,
        scale_match: str | None,
        position_match: str | None,
        direction_match: str | None,
        composition_match: bool,
        lighting_match: bool,
    ) -> SceneReferencePurpose:
        if reference.is_spatial_anchor:
            return SceneReferencePurpose.SPATIAL
        if composition_match:
            return SceneReferencePurpose.COMPOSITION
        if position_match is not None or direction_match is not None:
            return SceneReferencePurpose.CAMERA_REFERENCE
        if lighting_match:
            return SceneReferencePurpose.LIGHTING
        if reference.is_primary or (
            scale_match is not None
            and reference.shot_scale
            in {SceneShotScale.EXTREME_WIDE.value, SceneShotScale.WIDE.value}
        ):
            return SceneReferencePurpose.ENVIRONMENT
        return SceneReferencePurpose.GENERAL

    @staticmethod
    def _safe_tags(raw_tags: str) -> list[str]:
        import json

        try:
            value = json.loads(raw_tags or "[]")
        except json.JSONDecodeError:
            return []
        return [item for item in value if isinstance(item, str)]
