from app.api.schemas.prompt_builder import DirectorContext, PromptDraftWarning
from app.service.director.templates import ShotTemplate

DEFAULT_NEGATIVE_PROMPT_EN = (
    "low quality, blurry, distorted face, bad hands, extra fingers, text, watermark, "
    "logo, anime, cartoon, deformed body, inconsistent character, inconsistent clothing, "
    "flickering, camera jump"
)


def context_summary_zh(context: DirectorContext) -> str:
    subjects = "、".join(subject.identity for subject in context.subjects) or "未指定人物"
    scene = context.scene.name or "未指定场景"
    reaction = context.reaction.crowd_action or "未指定群众反应"
    return (
        f"导演结构：模板 {context.template_id}。主体：{subjects}。"
        f"场景：{scene}。构图：{context.camera.composition}。群众反应：{reaction}。"
    )


def first_frame_prompt(context: DirectorContext, template: ShotTemplate) -> str:
    return _frame_prompt(context, template, "first")


def end_frame_prompt(context: DirectorContext, template: ShotTemplate) -> str:
    return _frame_prompt(context, template, "end")


def motion_prompt(context: DirectorContext, template: ShotTemplate) -> str:
    subject_motion = [
        f"{subject.identity} moves from {subject.start_action} to {subject.end_action}"
        for subject in context.subjects
    ]
    parts = [
        "smooth cinematic short drama motion",
        *subject_motion,
        context.reaction.crowd_action,
        context.reaction.crowd_emotion,
        context.scene.environment_motion,
        context.camera.movement,
        context.camera.composition,
        *template.motion_fragments,
        "stable face, stable outfit, stable scene continuity",
    ]
    return join_prompt(parts)


def negative_prompt(include_negative_prompt: bool) -> str:
    return DEFAULT_NEGATIVE_PROMPT_EN if include_negative_prompt else ""


def merge_warnings(
    existing: list[PromptDraftWarning], director: list[PromptDraftWarning], template: ShotTemplate
) -> list[PromptDraftWarning]:
    result = [*existing, *director]
    for code in template.warnings:
        if code == "POSE_CONTROL_RECOMMENDED":
            result.append(
                PromptDraftWarning(
                    code=code,
                    message="该镜头模板建议使用姿态控制以稳定人物动作。",
                    severity="info",
                )
            )
        elif code == "SCENE_LAYOUT_CONFLICT_RISK":
            result.append(
                PromptDraftWarning(
                    code=code,
                    message="场景结构参考可能与人物动作构图冲突，建议弱化场景强控。",
                    severity="info",
                )
            )
    return unique_warnings(result)


def _frame_prompt(context: DirectorContext, template: ShotTemplate, frame: str) -> str:
    subject_parts = []
    for subject in context.subjects:
        action = subject.start_action if frame == "first" else subject.end_action
        expression = subject.expression_start if frame == "first" else subject.expression_end
        subject_parts.extend(
            [
                f"subject: {subject.identity}",
                f"look: {subject.look}" if subject.look else None,
                f"screen position: {subject.position}",
                f"action: {action}",
                f"expression: {expression}" if expression else None,
            ]
        )
    continuity = (
        "same character, same face, same outfit, same scene continuity"
        if frame == "end"
        else "clear first frame staging"
    )
    fragments = template.first_frame_fragments if frame == "first" else template.end_frame_fragments
    parts = [
        f"cinematic short drama {frame} frame",
        "vertical 9:16 composition",
        *subject_parts,
        context.reaction.crowd_action,
        f"crowd emotion: {context.reaction.crowd_emotion}"
        if context.reaction.crowd_emotion
        else None,
        f"scene: {context.scene.name}" if context.scene.name else None,
        context.scene.layout,
        context.camera.shot_scale,
        context.camera.angle,
        context.camera.height,
        f"{context.camera.lens} lens",
        context.camera.composition,
        context.scene.lighting,
        "realistic cinematic short drama style",
        *fragments,
        continuity,
        "high detail, natural skin texture",
    ]
    return join_prompt(parts)


def unique_warnings(warnings: list[PromptDraftWarning]) -> list[PromptDraftWarning]:
    seen: set[str] = set()
    result: list[PromptDraftWarning] = []
    for item in warnings:
        if item.code in seen:
            continue
        seen.add(item.code)
        result.append(item)
    return result


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


def clean(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""
