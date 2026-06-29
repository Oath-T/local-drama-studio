from app.api.schemas.keyframe_task import KeyframeShotSnapshot
from app.domain.keyframe_task import DEFAULT_NEGATIVE_PROMPT

SHOT_LABELS: dict[str, str] = {
    "extreme_wide": "大远景",
    "wide": "远景",
    "full": "全景",
    "medium_wide": "中远景",
    "medium": "中景",
    "medium_close": "中近景",
    "close": "近景",
    "close_up": "特写",
    "extreme_close_up": "大特写",
    "eye_level": "平视",
    "ground": "贴地机位",
    "low": "低机位",
    "high": "高机位",
    "overhead": "俯拍",
    "aerial": "航拍",
    "front": "正面",
    "back": "背面",
    "left_profile": "左侧面",
    "right_profile": "右侧面",
    "left_three_quarter": "左前侧",
    "right_three_quarter": "右前侧",
    "top_down": "顶视",
    "dutch_angle": "倾斜构图",
    "pov": "主观视角",
    "over_the_shoulder": "过肩视角",
    "centered": "居中构图",
    "symmetrical": "对称构图",
    "rule_of_thirds": "三分法构图",
    "leading_lines": "引导线构图",
    "frame_within_frame": "框中框构图",
    "layered": "层次构图",
    "negative_space": "留白构图",
    "close_blocking": "近距离调度",
    "static": "固定镜头",
    "push_in": "镜头推进",
    "pull_out": "镜头拉远",
    "pan_left": "向左摇镜",
    "pan_right": "向右摇镜",
    "tilt_up": "向上摇镜",
    "tilt_down": "向下摇镜",
    "tracking": "跟拍",
    "orbit": "环绕",
    "handheld": "手持感",
    "crane": "升降镜头",
    "zoom_in": "变焦推进",
    "zoom_out": "变焦拉远",
}


class KeyframePromptTemplateService:
    def build_prompt_zh(self, snapshot: KeyframeShotSnapshot) -> str:
        parts: list[str] = []
        sorted_characters = sorted(
            snapshot.characters,
            key=lambda item: (item.order_index, item.character_id),
        )
        for character in sorted_characters:
            character_parts = [
                character.character_name,
                character.look_name,
                character.action_description,
                character.expression_description,
                character.position_description,
            ]
            self._append_unique(parts, "，".join(self._clean_list(character_parts)))
        scene_parts = [
            snapshot.scene_name,
            snapshot.scene_state_name,
            snapshot.visual_description,
            snapshot.action_summary,
            snapshot.mood_description,
            self._enum_label(snapshot.shot_scale),
            self._enum_label(snapshot.camera_height, snapshot.custom_camera_height),
            self._enum_label(snapshot.camera_angle, snapshot.custom_camera_angle),
            self._enum_label(snapshot.composition_type, snapshot.custom_composition),
            self._enum_label(snapshot.camera_movement, snapshot.custom_camera_movement),
        ]
        for part in scene_parts:
            self._append_unique(parts, part)
        return "，".join(parts)

    def default_negative_prompt(self) -> str:
        return DEFAULT_NEGATIVE_PROMPT

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @classmethod
    def _clean_list(cls, values: list[str | None]) -> list[str]:
        return [value for value in (cls._clean(item) for item in values) if value]

    @staticmethod
    def _append_unique(parts: list[str], value: str | None) -> None:
        if value is None:
            return
        normalized = value.strip()
        if normalized and normalized not in parts:
            parts.append(normalized)

    @staticmethod
    def _enum_label(value: str, custom_value: str | None = None) -> str | None:
        if value in {"unknown", ""}:
            return None
        if value == "custom":
            return custom_value.strip() if custom_value and custom_value.strip() else None
        return SHOT_LABELS.get(value, value)
