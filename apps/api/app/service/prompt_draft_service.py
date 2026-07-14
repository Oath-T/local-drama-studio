from datetime import UTC, datetime
from uuid import UUID

from fastapi import status

from app.api.schemas.prompt_builder import (
    PromptDraftRequest,
    PromptDraftResponse,
    PromptDraftWarning,
)
from app.core.errors import AppError
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.shot import ShotRecord
from app.repository.prompt_context_repository import (
    PromptContextCharacterData,
    PromptContextData,
    PromptContextReferenceData,
    PromptContextRepository,
)
from app.service.director.composer import (
    context_summary_zh as director_context_summary_zh,
)
from app.service.director.composer import (
    end_frame_prompt as director_end_frame_prompt,
)
from app.service.director.composer import (
    first_frame_prompt as director_first_frame_prompt,
)
from app.service.director.composer import (
    merge_warnings as merge_director_warnings,
)
from app.service.director.composer import (
    motion_prompt as director_motion_prompt,
)
from app.service.director.composer import (
    negative_prompt as director_negative_prompt,
)
from app.service.director.context_builder import build_director_context
from app.service.director.matcher import recommend_template_id
from app.service.director.templates import get_template
from app.service.prompt_style_presets import get_style_preset

DEFAULT_NEGATIVE_PROMPT_EN = (
    "low quality, blurry, distorted face, bad hands, extra fingers, text, watermark, "
    "logo, anime, cartoon, deformed body, inconsistent character, inconsistent clothing, "
    "flickering, camera jump"
)

OVERRIDE_FIELDS = (
    "start_action",
    "end_action",
    "motion_direction",
    "camera_motion",
    "visual_style",
    "mood",
)

SHOT_SCALE_LABELS = {
    "unknown": "unspecified shot scale",
    "extreme_closeup": "extreme close-up",
    "closeup": "close-up",
    "medium_closeup": "medium close-up",
    "medium": "medium shot",
    "medium_wide": "medium wide shot",
    "wide": "wide shot",
    "extreme_wide": "extreme wide shot",
    "full": "full body shot",
}

CAMERA_ANGLE_LABELS = {
    "unknown": "neutral camera angle",
    "front": "front camera angle",
    "back": "back camera angle",
    "left_profile": "left profile camera angle",
    "right_profile": "right profile camera angle",
    "left_three_quarter": "left three-quarter camera angle",
    "right_three_quarter": "right three-quarter camera angle",
    "low_angle": "low angle",
    "top_down": "top-down angle",
    "dutch_angle": "dutch angle",
    "pov": "point-of-view camera angle",
    "over_the_shoulder": "over-the-shoulder camera angle",
}

CAMERA_HEIGHT_LABELS = {
    "unknown": "natural camera height",
    "eye_level": "eye-level camera height",
    "low": "low camera height",
    "high": "high camera height",
    "ground": "ground-level camera height",
}

COMPOSITION_LABELS = {
    "unknown": "balanced composition",
    "centered": "centered composition",
    "rule_of_thirds": "rule-of-thirds composition",
    "symmetrical": "symmetrical composition",
    "over_the_shoulder": "over-the-shoulder composition",
    "foreground_depth": "layered foreground depth",
}

CAMERA_MOVEMENT_LABELS = {
    "unknown": "subtle cinematic camera movement",
    "static": "locked-off stable camera",
    "push_in": "slow push-in",
    "pull_out": "slow pull-out",
    "pan_left": "slow pan left",
    "pan_right": "slow pan right",
    "tilt_up": "slow tilt up",
    "tilt_down": "slow tilt down",
    "handheld": "subtle handheld movement",
    "tracking": "smooth tracking movement",
}

TIME_LABELS = {
    "unknown": "unspecified time",
    "dawn": "dawn",
    "morning": "morning",
    "noon": "noon",
    "afternoon": "afternoon",
    "dusk": "dusk",
    "night": "night",
}

WEATHER_LABELS = {
    "unknown": "unspecified weather",
    "clear": "clear weather",
    "cloudy": "cloudy weather",
    "light_rain": "light rain",
    "heavy_rain": "heavy rain",
    "snow": "snow",
    "fog": "fog",
    "custom": "",
}

LIGHTING_LABELS = {
    "unknown": "unspecified lighting",
    "natural": "natural lighting",
    "soft": "soft lighting",
    "hard": "hard lighting",
    "neon": "neon lighting",
    "low_key": "low-key lighting",
    "high_key": "high-key lighting",
    "custom": "",
}


class PromptDraftService:
    def __init__(self, repository: PromptContextRepository) -> None:
        self.repository = repository

    def build_prompt_draft(
        self, project_id: UUID, shot_id: UUID, payload: PromptDraftRequest
    ) -> PromptDraftResponse:
        self._ensure_project(project_id)
        data = self.repository.get_context(str(project_id), str(shot_id))
        if data is None:
            raise AppError(
                code="SHOT_NOT_FOUND",
                message="镜头不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        warnings = self._warnings(data, payload)
        recommended_template_id = recommend_template_id(data.shot)
        template = get_template(payload.template_id or recommended_template_id)
        director_context, director_warnings = build_director_context(
            data=data,
            template=template,
            style=payload.style,
            director_overrides=payload.director_overrides,
            prompt_overrides=payload.overrides,
        )
        preset = get_style_preset(payload.style)
        negative_prompt = director_negative_prompt(payload.include_negative_prompt)
        first_prompt = join_prompt(
            [
                director_first_frame_prompt(director_context, template),
                phrase("first frame action", override_value(payload, "start_action")),
                preset.frame_fragment,
                phrase("visual style", override_value(payload, "visual_style")),
                phrase("mood", override_value(payload, "mood")),
            ]
        )
        end_prompt = join_prompt(
            [
                director_end_frame_prompt(director_context, template),
                phrase("ending action beat", override_value(payload, "end_action")),
                preset.frame_fragment,
                phrase("visual style", override_value(payload, "visual_style")),
                phrase("emotional change", override_value(payload, "mood")),
            ]
        )
        motion_prompt = join_prompt(
            [
                director_motion_prompt(director_context, template),
                phrase("motion direction", override_value(payload, "motion_direction")),
                preset.motion_fragment,
                phrase("visual style", override_value(payload, "visual_style")),
                phrase("emotional transition", override_value(payload, "mood")),
            ]
        )
        return PromptDraftResponse(
            source_shot_updated_at=ensure_utc(data.shot.updated_at),
            applied_style=preset.style,
            context_summary_zh=director_context_summary_zh(director_context),
            first_frame_prompt_en=first_prompt,
            end_frame_prompt_en=end_prompt,
            motion_prompt_en=motion_prompt,
            negative_prompt_en=negative_prompt,
            camera_motion=self._camera_motion(data.shot, payload),
            recommended_template_id=recommended_template_id,
            applied_template_id=template.id,
            workflow_hint=template.workflow_hint,
            director_context=director_context,
            warnings=merge_director_warnings(warnings, director_warnings, template),
        )

    def _ensure_project(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise AppError(
                code="PROJECT_NOT_FOUND",
                message="项目不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    def _context_summary_zh(self, data: PromptContextData) -> str:
        names = [item.character.name for item in data.characters if item.character]
        character_text = (
            f"当前镜头包含 {len(names)} 位人物：" + "、".join(names) + "。"
            if names
            else "当前镜头还没有绑定人物。"
        )
        scene_text = (
            f"场景为{data.scene.name}，状态为{data.state.name if data.state else '未指定'}。"
            if data.scene
            else "当前镜头还没有选择场景。"
        )
        action = text_or(data.shot.action_summary, "动作描述尚未填写")
        mood = text_or(data.shot.mood_description, "情绪氛围尚未填写")
        visual = text_or(data.shot.visual_description, "画面描述尚未填写")
        return (
            f"{character_text} {scene_text} "
            f"镜头画面：{visual}。镜头动作：{action}。情绪氛围：{mood}。"
        )

    def _first_frame_prompt(self, data: PromptContextData, payload: PromptDraftRequest) -> str:
        preset = get_style_preset(payload.style)
        start_action = override_value(payload, "start_action")
        parts = [
            "cinematic short drama first frame",
            "vertical 9:16 composition",
            self._shot_camera_text(data.shot),
            self._scene_prompt_text(data),
            self._character_prompt_text(data.characters),
            phrase("first frame action", start_action or data.shot.action_summary),
            phrase(
                "facial and emotional mood",
                override_value(payload, "mood") or data.shot.mood_description,
            ),
            phrase("visual description", data.shot.visual_description),
            phrase("focal subject", data.shot.focal_subject),
            preset.frame_fragment,
            phrase("visual style", override_value(payload, "visual_style")),
        ]
        return join_prompt(parts)

    def _end_frame_prompt(self, data: PromptContextData, payload: PromptDraftRequest) -> str:
        preset = get_style_preset(payload.style)
        end_action = override_value(payload, "end_action")
        parts = [
            "cinematic short drama end frame",
            "same character, same face, same outfit, same scene",
            "strong continuity from the first frame",
            "clear emotion transition while preserving identity",
            self._scene_prompt_text(data),
            self._character_prompt_text(data.characters),
            phrase("ending action beat", end_action or data.shot.action_summary),
            phrase(
                "emotional change",
                override_value(payload, "mood") or data.shot.mood_description,
            ),
            phrase("final visual state", data.shot.visual_description),
            phrase("focal subject", data.shot.focal_subject),
            preset.frame_fragment,
            phrase("visual style", override_value(payload, "visual_style")),
            "avoid face change, avoid outfit change, stable identity continuity",
        ]
        return join_prompt(parts)

    def _motion_prompt(self, data: PromptContextData, payload: PromptDraftRequest) -> str:
        preset = get_style_preset(payload.style)
        parts = [
            "smooth cinematic short drama motion",
            self._camera_motion(data.shot, payload),
            self._character_motion_text(data.characters),
            phrase("motion direction", override_value(payload, "motion_direction")),
            phrase("main action change", data.shot.action_summary),
            phrase(
                "emotional transition",
                override_value(payload, "mood") or data.shot.mood_description,
            ),
            self._environment_motion_text(data),
            preset.motion_fragment,
            phrase("visual style", override_value(payload, "visual_style")),
            "smooth transition between first and end frame",
            "stable facial expression continuity",
            "natural environmental motion",
            (
                "keep same face, keep same outfit, avoid flicker, avoid jump cut, "
                "avoid camera jump, stable framing"
            ),
        ]
        return join_prompt(parts)

    def _shot_camera_text(self, shot: ShotRecord) -> str:
        parts = [
            label_or_custom(shot.shot_scale, None, SHOT_SCALE_LABELS),
            label_or_custom(shot.camera_angle, shot.custom_camera_angle, CAMERA_ANGLE_LABELS),
            label_or_custom(shot.camera_height, shot.custom_camera_height, CAMERA_HEIGHT_LABELS),
            label_or_custom(shot.composition_type, shot.custom_composition, COMPOSITION_LABELS),
        ]
        return join_prompt(parts)

    def _scene_prompt_text(self, data: PromptContextData) -> str:
        if data.scene is None:
            return "unspecified scene"
        parts = [
            f"scene: {data.scene.name}",
            data.scene.prompt_environment,
            data.scene.fixed_environment_description,
            data.scene.spatial_layout_description,
            data.scene.visual_style_description,
        ]
        if data.state:
            weather = label_or_custom(data.state.weather, data.state.custom_weather, WEATHER_LABELS)
            lighting = label_or_custom(
                data.state.lighting, data.state.custom_lighting, LIGHTING_LABELS
            )
            parts.extend(
                [
                    f"scene state: {data.state.name}",
                    data.state.prompt_state,
                    label_or_custom(data.state.time_of_day, None, TIME_LABELS),
                    weather,
                    lighting,
                    data.state.environment_condition,
                    f"crowd level: {data.state.crowd_level}",
                ]
            )
        return join_prompt(parts)

    def _character_prompt_text(self, characters: list[PromptContextCharacterData]) -> str:
        if not characters:
            return "no character is currently bound to this shot"
        lines: list[str] = []
        for item in characters:
            if item.character is None:
                lines.append("deleted character binding")
                continue
            look = item.look
            parts = [
                f"character {item.character.name}",
                item.character.prompt_identity,
                item.character.appearance_description,
                f"look {look.name}" if look else None,
                look.prompt_appearance if look else None,
                look.costume_description if look else None,
                look.hair_description if look else None,
                look.makeup_description if look else None,
                look.condition_description if look else None,
                phrase("action", item.shot_character.action_description),
                phrase("expression", item.shot_character.expression_description),
                phrase("position", item.shot_character.position_description),
                "primary subject" if item.shot_character.is_primary_subject else None,
            ]
            lines.append(join_prompt(parts))
        return join_prompt(lines)

    def _character_motion_text(self, characters: list[PromptContextCharacterData]) -> str:
        parts: list[str] = []
        for item in characters:
            name = item.character.name if item.character else "character"
            parts.extend(
                [
                    f"{name} action: {item.shot_character.action_description}"
                    if clean(item.shot_character.action_description)
                    else None,
                    f"{name} expression change: {item.shot_character.expression_description}"
                    if clean(item.shot_character.expression_description)
                    else None,
                    f"{name} screen position: {item.shot_character.position_description}"
                    if clean(item.shot_character.position_description)
                    else None,
                ]
            )
        return join_prompt(parts) or "subtle character movement"

    def _environment_motion_text(self, data: PromptContextData) -> str:
        if data.state is None:
            return "subtle atmospheric movement"
        weather = label_or_custom(data.state.weather, data.state.custom_weather, WEATHER_LABELS)
        lighting = label_or_custom(data.state.lighting, data.state.custom_lighting, LIGHTING_LABELS)
        parts = [
            f"environment motion from {weather}" if weather else None,
            f"lighting atmosphere: {lighting}" if lighting else None,
            data.state.environment_condition,
        ]
        return join_prompt(parts) or "subtle atmospheric movement"

    def _camera_motion(self, shot: ShotRecord, payload: PromptDraftRequest | None = None) -> str:
        override = override_value(payload, "camera_motion") if payload else None
        if override:
            return override
        if shot.camera_movement == "custom" and clean(shot.custom_camera_movement):
            return str(shot.custom_camera_movement).strip()
        label = CAMERA_MOVEMENT_LABELS.get(shot.camera_movement)
        if label and shot.camera_movement != "unknown":
            return label
        return "subtle cinematic camera movement, stable framing"

    def _warnings(
        self, data: PromptContextData, payload: PromptDraftRequest
    ) -> list[PromptDraftWarning]:
        warnings: list[PromptDraftWarning] = []
        if has_overrides(payload):
            warnings.append(warning("OVERRIDE_USED", "已使用本次生成覆盖项。", "info"))
        if payload.style != "cinematic_short_drama":
            warnings.append(warning("STYLE_PRESET_USED", "已使用风格预设。", "info"))
        if not data.characters:
            warnings.append(warning("NO_CHARACTERS", "镜头还没有参与人物。"))
        for item in data.characters:
            if item.look is None:
                warnings.append(warning("CHARACTER_LOOK_MISSING", "人物未指定可用造型。"))
            if not self._character_references_for(data.references, item.shot_character.id):
                warnings.append(warning("CHARACTER_REFERENCE_MISSING", "人物缺少已绑定参考图。"))
        if not any(
            ref.character_reference and ref.character_reference.is_identity_anchor
            for ref in data.references
        ):
            warnings.append(warning("IDENTITY_REFERENCE_MISSING", "缺少身份基准图。"))
        if data.scene is None:
            warnings.append(warning("SCENE_MISSING", "镜头未选择场景。"))
        if data.scene is not None and data.state is None:
            warnings.append(warning("SCENE_STATE_MISSING", "镜头未选择场景状态。"))
        if data.state and not any(ref.scene_reference for ref in data.references):
            warnings.append(warning("SCENE_REFERENCE_MISSING", "缺少场景参考图。"))
        if data.state and not any(
            ref.scene_reference and ref.scene_reference.is_spatial_anchor for ref in data.references
        ):
            warnings.append(warning("SPATIAL_REFERENCE_MISSING", "缺少空间结构参考图。"))
        if not clean(data.shot.visual_description):
            warnings.append(warning("SHOT_VISUAL_DESCRIPTION_MISSING", "缺少画面描述。"))
        if not clean(data.shot.action_summary):
            warnings.append(warning("SHOT_ACTION_MISSING", "缺少动作描述。"))
        if not override_value(payload, "end_action") and not any(
            clean(value)
            for value in [
                data.shot.action_summary,
                data.shot.mood_description,
                data.shot.visual_description,
                data.shot.focal_subject,
            ]
        ):
            warnings.append(warning("WEAK_END_FRAME_SIGNAL", "缺少明确尾帧变化依据。"))
        if data.shot.camera_movement == "unknown" and not clean(data.shot.custom_camera_movement):
            warnings.append(warning("NO_CAMERA_MOTION", "缺少镜头运动描述。", "info"))
        return unique_warnings(warnings)

    def _character_references_for(
        self, references: list[PromptContextReferenceData], shot_character_id: str
    ) -> list[CharacterReferenceRecord]:
        return [
            ref.character_reference
            for ref in references
            if ref.shot_reference.shot_character_id == shot_character_id
            and ref.character_reference is not None
        ]


def warning(code: str, message: str, severity: str = "warning") -> PromptDraftWarning:
    return PromptDraftWarning(code=code, message=message, severity=severity)


def unique_warnings(warnings: list[PromptDraftWarning]) -> list[PromptDraftWarning]:
    seen: set[str] = set()
    result: list[PromptDraftWarning] = []
    for item in warnings:
        if item.code in seen:
            continue
        seen.add(item.code)
        result.append(item)
    return result


def has_overrides(payload: PromptDraftRequest) -> bool:
    return any(override_value(payload, field) for field in OVERRIDE_FIELDS)


def override_value(payload: PromptDraftRequest | None, field: str) -> str | None:
    if payload is None or payload.overrides is None:
        return None
    value = getattr(payload.overrides, field)
    return clean(value) or None


def label_or_custom(value: str | None, custom: str | None, labels: dict[str, str]) -> str:
    if value == "custom" and clean(custom):
        return str(custom).strip()
    if value is None:
        return ""
    return labels.get(value, value.replace("_", " "))


def phrase(label: str, value: str | None) -> str | None:
    text = clean(value)
    return f"{label}: {text}" if text else None


def text_or(value: str | None, fallback: str) -> str:
    return clean(value) or fallback


def clean(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


def join_prompt(parts: list[str | None]) -> str:
    cleaned = [clean(part) for part in parts if clean(part)]
    seen: set[str] = set()
    result: list[str] = []
    for item in cleaned:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return ", ".join(result)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
