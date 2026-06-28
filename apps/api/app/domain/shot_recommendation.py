from __future__ import annotations

import re
from enum import StrEnum


class SceneRecommendationStatus(StrEnum):
    READY = "ready"
    SCENE_STATE_REQUIRED = "scene_state_required"
    NO_REFERENCES = "no_references"


class RecommendationReason(StrEnum):
    LOOK_EXACT_MATCH = "look_exact_match"
    DIFFERENT_LOOK = "different_look"
    SHOT_SCALE_EXACT = "shot_scale_exact"
    SHOT_SCALE_CLOSE = "shot_scale_close"
    VIEW_ANGLE_EXACT = "view_angle_exact"
    VIEW_ANGLE_CLOSE = "view_angle_close"
    IDENTITY_ANCHOR = "identity_anchor"
    PRIMARY_REFERENCE = "primary_reference"
    EXPRESSION_MATCH = "expression_match"
    POSE_MATCH = "pose_match"
    ALREADY_BOUND_OTHER_PURPOSE = "already_bound_other_purpose"
    CAMERA_POSITION_EXACT = "camera_position_exact"
    CAMERA_POSITION_CLOSE = "camera_position_close"
    VIEW_DIRECTION_EXACT = "view_direction_exact"
    VIEW_DIRECTION_CLOSE = "view_direction_close"
    COMPOSITION_EXACT = "composition_exact"
    SPATIAL_ANCHOR = "spatial_anchor"
    EMPTY_PLATE = "empty_plate"
    KEYWORD_MATCH = "keyword_match"


PUNCTUATION_PATTERN = re.compile(r"[\s,.;:!?，。；：！？、（）()【】\[\]{}<>《》\"'“”‘’]+")


KEYWORD_DICTIONARY: dict[str, dict[str, tuple[str, ...]]] = {
    "expression": {
        "neutral": ("neutral", "平静", "冷静", "无表情"),
        "happy": ("happy", "开心", "高兴", "喜悦"),
        "smile": ("smile", "微笑", "笑容"),
        "sad": ("sad", "悲伤", "难过"),
        "angry": ("angry", "愤怒", "生气"),
        "shocked": ("shocked", "震惊", "惊讶"),
        "fearful": ("fearful", "恐惧", "害怕"),
        "crying": ("crying", "哭", "流泪"),
        "serious": ("serious", "严肃", "凝重"),
        "cold_smirk": ("cold smirk", "冷笑"),
    },
    "pose": {
        "standing": ("standing", "站立", "站着"),
        "sitting": ("sitting", "坐着", "坐下"),
        "walking": ("walking", "行走", "走路"),
        "looking_camera": ("looking camera", "看镜头", "直视"),
        "looking_away": ("looking away", "看向别处", "移开视线"),
        "holding_object": ("holding object", "拿着", "握着"),
    },
    "lighting": {
        "neon": ("neon", "霓虹"),
        "low_key": ("low key", "低调光", "暗光"),
        "high_key": ("high key", "高调光", "明亮"),
        "backlight": ("backlight", "背光", "逆光"),
        "warm": ("warm light", "暖光", "暖色"),
        "cool": ("cool light", "冷光", "冷色"),
        "natural": ("natural light", "自然光"),
    },
}


def normalize_recommendation_text(parts: list[str | None]) -> str:
    joined = " ".join(part.strip() for part in parts if part and part.strip())
    normalized = PUNCTUATION_PATTERN.sub(" ", joined.lower())
    return f" {normalized.strip()} " if normalized.strip() else ""


def text_matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    if not text:
        return False
    for keyword in keywords:
        value = keyword.strip().lower()
        if not value:
            continue
        if len(value) == 1 and value not in {"哭"}:
            continue
        normalized = PUNCTUATION_PATTERN.sub(" ", value)
        if re.search(r"[\u4e00-\u9fff]", normalized):
            if normalized in text:
                return True
        elif f" {normalized} " in text:
            return True
    return False


def matched_keyword_categories(
    dictionary_name: str,
    shot_text: str,
    candidate_text: str,
) -> set[str]:
    matches: set[str] = set()
    for category, keywords in KEYWORD_DICTIONARY[dictionary_name].items():
        if text_matches_keywords(shot_text, keywords) and text_matches_keywords(
            candidate_text, keywords
        ):
            matches.add(category)
    return matches


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
