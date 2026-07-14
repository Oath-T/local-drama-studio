from app.api.schemas.prompt_builder import (
    DirectorCamera,
    DirectorContext,
    DirectorOverrides,
    DirectorReaction,
    DirectorScene,
    DirectorStyle,
    DirectorSubject,
    PromptDraftOverrides,
    PromptDraftStyle,
    PromptDraftWarning,
)
from app.repository.prompt_context_repository import PromptContextData
from app.service.director.templates import ShotTemplate

SHOT_SCALE_LABELS = {
    "unknown": "unspecified shot scale",
    "medium_wide": "medium wide shot",
    "wide": "wide shot",
    "medium": "medium shot",
    "medium_closeup": "medium close-up",
    "closeup": "close-up",
    "full": "full body shot",
}

ANGLE_LABELS = {
    "unknown": "eye-level camera angle",
    "front": "front angle",
    "low_angle": "low angle",
    "over_the_shoulder": "over-the-shoulder angle",
}

HEIGHT_LABELS = {
    "unknown": "eye-level camera height",
    "eye_level": "eye-level camera height",
    "low": "low camera height",
    "high": "high camera height",
}

CAMERA_MOVEMENT_LABELS = {
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


def build_director_context(
    data: PromptContextData,
    template: ShotTemplate,
    style: PromptDraftStyle,
    director_overrides: DirectorOverrides | None,
    prompt_overrides: PromptDraftOverrides | None,
) -> tuple[DirectorContext, list[PromptDraftWarning]]:
    warnings: list[PromptDraftWarning] = []
    subjects = _subjects(data, template, director_overrides, prompt_overrides, warnings)
    scene = _scene(data, template, director_overrides, warnings)
    reaction = _reaction(template, director_overrides, warnings)
    camera = _camera(data, template, director_overrides, prompt_overrides, warnings)
    context = DirectorContext(
        shot_id=data.shot.id,
        template_id=template.id,
        subjects=subjects,
        scene=scene,
        reaction=reaction,
        camera=camera,
        style=DirectorStyle(preset=style),
    )
    return context, warnings


def _subjects(
    data: PromptContextData,
    template: ShotTemplate,
    director_overrides: DirectorOverrides | None,
    prompt_overrides: PromptDraftOverrides | None,
    warnings: list[PromptDraftWarning],
) -> list[DirectorSubject]:
    if not data.characters:
        warnings.append(warning("NO_PRIMARY_SUBJECT", "缺少镜头主角。"))
        return []
    primary = next(
        (item for item in data.characters if item.shot_character.is_primary_subject), None
    )
    if primary is None:
        warnings.append(
            warning("NO_PRIMARY_SUBJECT", "镜头没有标记主角，已使用第一个人物作为导演主体。")
        )
        primary = data.characters[0]
    result: list[DirectorSubject] = []
    for item in data.characters:
        name = item.character.name if item.character else "character"
        look = item.look.name if item.look else None
        is_primary = item.shot_character.id == primary.shot_character.id
        start_action = first_text(
            director_overrides.start_action if director_overrides else None,
            prompt_overrides.start_action if prompt_overrides else None,
            item.shot_character.action_description,
            data.shot.action_summary,
            template.start_action_template.format(primary=name),
        )
        end_action = first_text(
            director_overrides.end_action if director_overrides else None,
            prompt_overrides.end_action if prompt_overrides else None,
            data.shot.visual_description,
            template.end_action_template.format(primary=name),
        )
        position = first_text(
            director_overrides.subject_position if director_overrides else None,
            item.shot_character.position_description,
            template.subject_position,
        )
        if not clean(item.shot_character.position_description) and not (
            director_overrides and clean(director_overrides.subject_position)
        ):
            warnings.append(
                warning("SUBJECT_POSITION_MISSING", "人物缺少明确画面位置，已使用模板默认位置。")
            )
        if not clean(start_action):
            warnings.append(warning("START_ACTION_MISSING", "缺少首帧动作。"))
        if not clean(end_action):
            warnings.append(warning("END_ACTION_MISSING", "缺少尾帧动作。"))
        result.append(
            DirectorSubject(
                shot_character_id=item.shot_character.id,
                character_id=item.character.id if item.character else None,
                role="primary" if is_primary else "supporting",
                identity=first_text(
                    name,
                    item.character.prompt_identity if item.character else None,
                    item.character.description if item.character else None,
                ),
                look=first_text(
                    item.look.prompt_appearance if item.look else None,
                    item.look.costume_description if item.look else None,
                    look,
                ),
                position=position,
                start_action=start_action,
                end_action=end_action,
                expression_start=item.shot_character.expression_description,
                expression_end=first_text(
                    prompt_overrides.mood if prompt_overrides else None,
                    data.shot.mood_description,
                    item.shot_character.expression_description,
                ),
            )
        )
    return result


def _scene(
    data: PromptContextData,
    template: ShotTemplate,
    director_overrides: DirectorOverrides | None,
    warnings: list[PromptDraftWarning],
) -> DirectorScene:
    if data.scene is None:
        warnings.append(warning("SCENE_MISSING", "镜头未选择场景。"))
    if data.scene and not clean(data.scene.spatial_layout_description):
        warnings.append(
            warning(
                "SCENE_LAYOUT_CONFLICT_RISK", "场景缺少明确空间布局，强结构控制可能不稳定。", "info"
            )
        )
    lighting = None
    if data.state:
        lighting = label_or_custom(
            data.state.lighting,
            data.state.custom_lighting,
            {
                "unknown": "",
                "natural": "natural lighting",
                "soft": "soft lighting",
                "hard": "hard lighting",
                "neon": "neon lighting",
                "low_key": "low-key lighting",
                "high_key": "high-key lighting",
                "custom": "",
            },
        )
    return DirectorScene(
        scene_id=data.scene.id if data.scene else None,
        state_id=data.state.id if data.state else None,
        name=data.scene.name if data.scene else None,
        state=data.state.name if data.state else None,
        layout=first_text(
            data.scene.spatial_layout_description if data.scene else None,
            data.scene.fixed_environment_description if data.scene else None,
            template.composition,
        ),
        lighting=first_text(
            data.state.prompt_state if data.state else None,
            lighting,
            data.scene.visual_style_description if data.scene else None,
        ),
        environment_motion=first_text(
            director_overrides.environment_motion if director_overrides else None,
            data.state.environment_condition if data.state else None,
            "subtle atmospheric movement",
        ),
    )


def _reaction(
    template: ShotTemplate,
    director_overrides: DirectorOverrides | None,
    warnings: list[PromptDraftWarning],
) -> DirectorReaction:
    crowd_action = first_text(
        director_overrides.crowd_action if director_overrides else None,
        template.crowd_action,
    )
    crowd_emotion = first_text(
        director_overrides.crowd_emotion if director_overrides else None,
        template.crowd_emotion,
    )
    if not crowd_action and not crowd_emotion:
        warnings.append(warning("CROWD_REACTION_MISSING", "缺少群众反应。", "info"))
    return DirectorReaction(crowd_action=crowd_action, crowd_emotion=crowd_emotion)


def _camera(
    data: PromptContextData,
    template: ShotTemplate,
    director_overrides: DirectorOverrides | None,
    prompt_overrides: PromptDraftOverrides | None,
    warnings: list[PromptDraftWarning],
) -> DirectorCamera:
    composition = first_text(
        director_overrides.composition if director_overrides else None,
        data.shot.custom_composition if data.shot.composition_type == "custom" else None,
        template.composition,
    )
    if not clean(composition):
        warnings.append(warning("CAMERA_COMPOSITION_MISSING", "缺少明确构图。"))
    return DirectorCamera(
        shot_scale=SHOT_SCALE_LABELS.get(data.shot.shot_scale, template.recommended_shot_scale),
        angle=label_or_custom(data.shot.camera_angle, data.shot.custom_camera_angle, ANGLE_LABELS),
        height=label_or_custom(
            data.shot.camera_height, data.shot.custom_camera_height, HEIGHT_LABELS
        ),
        lens=template.lens,
        composition=composition,
        movement=first_text(
            director_overrides.camera_movement if director_overrides else None,
            prompt_overrides.camera_motion if prompt_overrides else None,
            data.shot.custom_camera_movement if data.shot.camera_movement == "custom" else None,
            CAMERA_MOVEMENT_LABELS.get(data.shot.camera_movement),
            "subtle cinematic camera movement, stable framing",
        ),
    )


def first_text(*values: str | None) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def clean(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


def label_or_custom(value: str | None, custom: str | None, labels: dict[str, str]) -> str:
    if value == "custom" and clean(custom):
        return str(custom).strip()
    if value is None:
        return ""
    return labels.get(value, value.replace("_", " "))


def warning(code: str, message: str, severity: str = "warning") -> PromptDraftWarning:
    return PromptDraftWarning(code=code, message=message, severity=severity)
