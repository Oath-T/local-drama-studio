from dataclasses import dataclass

from app.domain.character import Expression, PoseType, ShotType, ViewAngle
from app.domain.shot import CharacterReferencePurpose, ShotScale
from app.domain.shot_recommendation import (
    KEYWORD_DICTIONARY,
    RecommendationReason,
    matched_keyword_categories,
    normalize_recommendation_text,
    stable_unique,
    text_matches_keywords,
)
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord


@dataclass(frozen=True)
class CharacterRankResult:
    score: int
    suggested_purpose: CharacterReferencePurpose
    reasons: list[str]


CHARACTER_SHOT_SCALE_GROUPS: dict[str, set[str]] = {
    "face": {
        ShotScale.CLOSE.value,
        ShotScale.CLOSE_UP.value,
        ShotScale.EXTREME_CLOSE_UP.value,
        ShotScale.MEDIUM_CLOSE.value,
    },
    "body": {
        ShotScale.MEDIUM.value,
        ShotScale.MEDIUM_WIDE.value,
        ShotScale.FULL.value,
    },
    "wide": {
        ShotScale.WIDE.value,
        ShotScale.EXTREME_WIDE.value,
    },
}

REFERENCE_SHOT_GROUPS: dict[str, str] = {
    ShotType.FACE_CLOSEUP.value: "face",
    ShotType.CLOSEUP.value: "face",
    ShotType.UPPER_BODY.value: "body",
    ShotType.HALF_BODY.value: "body",
    ShotType.THREE_QUARTER.value: "body",
    ShotType.FULL_BODY.value: "body",
}

SHOT_SCALE_EXACT: dict[str, set[str]] = {
    ShotScale.EXTREME_CLOSE_UP.value: {ShotType.FACE_CLOSEUP.value},
    ShotScale.CLOSE_UP.value: {ShotType.FACE_CLOSEUP.value, ShotType.CLOSEUP.value},
    ShotScale.CLOSE.value: {ShotType.CLOSEUP.value},
    ShotScale.MEDIUM_CLOSE.value: {ShotType.UPPER_BODY.value},
    ShotScale.MEDIUM.value: {ShotType.HALF_BODY.value, ShotType.UPPER_BODY.value},
    ShotScale.MEDIUM_WIDE.value: {ShotType.THREE_QUARTER.value},
    ShotScale.FULL.value: {ShotType.FULL_BODY.value},
    ShotScale.WIDE.value: {ShotType.FULL_BODY.value},
    ShotScale.EXTREME_WIDE.value: {ShotType.FULL_BODY.value},
}

VIEW_ANGLE_EXACT: dict[str, set[str]] = {
    "front": {ViewAngle.FRONT.value},
    "back": {ViewAngle.BACK.value},
    "left_profile": {ViewAngle.LEFT_PROFILE.value},
    "right_profile": {ViewAngle.RIGHT_PROFILE.value},
    "left_three_quarter": {ViewAngle.LEFT_45.value},
    "right_three_quarter": {ViewAngle.RIGHT_45.value},
}

VIEW_ANGLE_CLOSE: dict[str, set[str]] = {
    "front": {ViewAngle.LEFT_45.value, ViewAngle.RIGHT_45.value},
    "left_three_quarter": {ViewAngle.FRONT.value, ViewAngle.LEFT_PROFILE.value},
    "right_three_quarter": {ViewAngle.FRONT.value, ViewAngle.RIGHT_PROFILE.value},
    "left_profile": {ViewAngle.LEFT_45.value},
    "right_profile": {ViewAngle.RIGHT_45.value},
}

IDENTITY_SAFE_EXPRESSIONS = {
    Expression.NEUTRAL.value,
    Expression.SERIOUS.value,
    Expression.SMILE.value,
    Expression.UNKNOWN.value,
}

BODY_REFERENCE_TYPES = {
    ShotType.UPPER_BODY.value,
    ShotType.HALF_BODY.value,
    ShotType.THREE_QUARTER.value,
    ShotType.FULL_BODY.value,
}


class CharacterReferenceRanker:
    def rank(
        self,
        shot: ShotRecord,
        shot_character: ShotCharacterRecord,
        reference: CharacterReferenceRecord,
    ) -> CharacterRankResult:
        score = 0
        reasons: list[str] = []
        applied: set[RecommendationReason] = set()

        look_exact = (
            shot_character.look_id is not None and reference.look_id == shot_character.look_id
        )
        if look_exact:
            score += self._add_reason(applied, reasons, RecommendationReason.LOOK_EXACT_MATCH, 40)
        elif shot_character.look_id is not None:
            self._add_reason(applied, reasons, RecommendationReason.DIFFERENT_LOOK, 0)

        scale_match = self._score_shot_scale(shot.shot_scale, reference.shot_type)
        if scale_match == "exact":
            score += self._add_reason(applied, reasons, RecommendationReason.SHOT_SCALE_EXACT, 20)
        elif scale_match == "close":
            score += self._add_reason(applied, reasons, RecommendationReason.SHOT_SCALE_CLOSE, 12)

        angle_match = self._score_view_angle(shot.camera_angle, reference.view_angle)
        if angle_match == "exact":
            score += self._add_reason(applied, reasons, RecommendationReason.VIEW_ANGLE_EXACT, 15)
        elif angle_match == "close":
            score += self._add_reason(applied, reasons, RecommendationReason.VIEW_ANGLE_CLOSE, 8)

        if reference.is_identity_anchor:
            score += self._add_reason(applied, reasons, RecommendationReason.IDENTITY_ANCHOR, 10)
        if reference.is_primary:
            score += self._add_reason(applied, reasons, RecommendationReason.PRIMARY_REFERENCE, 5)

        shot_text = normalize_recommendation_text(
            [
                shot.visual_description,
                shot.story_description,
                shot.mood_description,
                shot.action_summary,
                shot_character.expression_description,
                shot_character.action_description,
                shot_character.position_description,
            ]
        )
        candidate_text = normalize_recommendation_text(
            [
                " ".join(self._safe_tags(reference.tags)),
                reference.description,
                reference.expression,
                reference.pose_type,
            ]
        )
        expression_match = self._matches_expression(shot_text, candidate_text, reference.expression)
        pose_match = self._matches_pose(shot_text, candidate_text, reference.pose_type)
        if expression_match:
            score += self._add_reason(applied, reasons, RecommendationReason.EXPRESSION_MATCH, 10)
        if pose_match:
            score += self._add_reason(applied, reasons, RecommendationReason.POSE_MATCH, 5)

        purpose = self._suggest_purpose(
            reference=reference,
            look_exact=look_exact,
            scale_match=scale_match,
            angle_match=angle_match,
            expression_match=expression_match,
            pose_match=pose_match,
        )
        return CharacterRankResult(
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
    def _score_shot_scale(shot_scale: str, reference_shot_type: str) -> str | None:
        if shot_scale == ShotScale.UNKNOWN.value or reference_shot_type == ShotType.UNKNOWN.value:
            return None
        if reference_shot_type in SHOT_SCALE_EXACT.get(shot_scale, set()):
            return "exact"
        shot_group = next(
            (
                group
                for group, values in CHARACTER_SHOT_SCALE_GROUPS.items()
                if shot_scale in values
            ),
            None,
        )
        reference_group = REFERENCE_SHOT_GROUPS.get(reference_shot_type)
        return "close" if shot_group and shot_group == reference_group else None

    @staticmethod
    def _score_view_angle(camera_angle: str, view_angle: str) -> str | None:
        if view_angle in VIEW_ANGLE_EXACT.get(camera_angle, set()):
            return "exact"
        if view_angle in VIEW_ANGLE_CLOSE.get(camera_angle, set()):
            return "close"
        return None

    @staticmethod
    def _matches_expression(shot_text: str, candidate_text: str, expression: str) -> bool:
        if expression in {Expression.UNKNOWN.value, Expression.CUSTOM.value}:
            return bool(matched_keyword_categories("expression", shot_text, candidate_text))
        keywords = KEYWORD_DICTIONARY["expression"].get(expression, ())
        return text_matches_keywords(shot_text, keywords) and (
            text_matches_keywords(candidate_text, keywords) or expression in candidate_text
        )

    @staticmethod
    def _matches_pose(shot_text: str, candidate_text: str, pose_type: str) -> bool:
        if pose_type in {PoseType.UNKNOWN.value, PoseType.CUSTOM.value}:
            return bool(matched_keyword_categories("pose", shot_text, candidate_text))
        keywords = KEYWORD_DICTIONARY["pose"].get(pose_type, ())
        return text_matches_keywords(shot_text, keywords) and (
            text_matches_keywords(candidate_text, keywords) or pose_type in candidate_text
        )

    @staticmethod
    def _suggest_purpose(
        reference: CharacterReferenceRecord,
        look_exact: bool,
        scale_match: str | None,
        angle_match: str | None,
        expression_match: bool,
        pose_match: bool,
    ) -> CharacterReferencePurpose:
        if expression_match:
            return CharacterReferencePurpose.EXPRESSION
        if pose_match:
            return CharacterReferencePurpose.POSE
        if reference.is_identity_anchor or (
            angle_match == "exact"
            and reference.view_angle == ViewAngle.FRONT.value
            and reference.shot_type in {ShotType.FACE_CLOSEUP.value, ShotType.CLOSEUP.value}
            and reference.expression in IDENTITY_SAFE_EXPRESSIONS
        ):
            return CharacterReferencePurpose.IDENTITY
        if look_exact and reference.shot_type in BODY_REFERENCE_TYPES:
            return CharacterReferencePurpose.APPEARANCE
        if scale_match is not None:
            return CharacterReferencePurpose.FRAMING
        return CharacterReferencePurpose.GENERAL

    @staticmethod
    def _safe_tags(raw_tags: str) -> list[str]:
        import json

        try:
            value = json.loads(raw_tags or "[]")
        except json.JSONDecodeError:
            return []
        return [item for item in value if isinstance(item, str)]
