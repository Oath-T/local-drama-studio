from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PromptDraftTarget = Literal["keyframe", "video", "all"]
PromptDraftStyle = Literal[
    "cinematic_short_drama",
    "ultra_realistic",
    "rain_night_neon",
    "office_drama",
    "emotional_closeup",
    "action_tension",
]
PromptDraftLanguage = Literal["en"]
PromptDraftWarningSeverity = Literal["info", "warning"]


class PromptDraftOverrides(BaseModel):
    start_action: str | None = Field(default=None, max_length=1000)
    end_action: str | None = Field(default=None, max_length=1000)
    motion_direction: str | None = Field(default=None, max_length=1000)
    camera_motion: str | None = Field(default=None, max_length=1000)
    visual_style: str | None = Field(default=None, max_length=1000)
    mood: str | None = Field(default=None, max_length=1000)


class DirectorOverrides(BaseModel):
    subject_position: str | None = Field(default=None, max_length=1000)
    start_action: str | None = Field(default=None, max_length=1000)
    end_action: str | None = Field(default=None, max_length=1000)
    crowd_action: str | None = Field(default=None, max_length=1000)
    crowd_emotion: str | None = Field(default=None, max_length=1000)
    camera_movement: str | None = Field(default=None, max_length=1000)
    composition: str | None = Field(default=None, max_length=1000)
    environment_motion: str | None = Field(default=None, max_length=1000)


class PromptDraftRequest(BaseModel):
    target: PromptDraftTarget = "all"
    style: PromptDraftStyle = "cinematic_short_drama"
    language: PromptDraftLanguage = "en"
    include_negative_prompt: bool = True
    overrides: PromptDraftOverrides | None = None
    template_id: str | None = Field(default=None, max_length=80)
    director_overrides: DirectorOverrides | None = None


class PromptDraftWarning(BaseModel):
    code: str
    message: str
    severity: PromptDraftWarningSeverity


class DirectorSubject(BaseModel):
    shot_character_id: str | None = None
    character_id: str | None = None
    role: str
    identity: str
    look: str | None = None
    position: str
    start_action: str
    end_action: str
    expression_start: str | None = None
    expression_end: str | None = None


class DirectorScene(BaseModel):
    scene_id: str | None = None
    state_id: str | None = None
    name: str | None = None
    state: str | None = None
    layout: str | None = None
    lighting: str | None = None
    environment_motion: str | None = None


class DirectorReaction(BaseModel):
    crowd_action: str | None = None
    crowd_emotion: str | None = None


class DirectorCamera(BaseModel):
    shot_scale: str
    angle: str
    height: str
    lens: str
    composition: str
    movement: str


class DirectorStyle(BaseModel):
    preset: PromptDraftStyle
    aspect_ratio: str = "9:16"


class DirectorContext(BaseModel):
    shot_id: str
    template_id: str
    subjects: list[DirectorSubject] = Field(default_factory=list)
    scene: DirectorScene
    reaction: DirectorReaction
    camera: DirectorCamera
    style: DirectorStyle


class PromptDraftResponse(BaseModel):
    source_shot_updated_at: datetime
    applied_style: PromptDraftStyle
    context_summary_zh: str
    first_frame_prompt_en: str
    end_frame_prompt_en: str
    motion_prompt_en: str
    negative_prompt_en: str
    camera_motion: str | None
    recommended_template_id: str
    applied_template_id: str
    workflow_hint: str
    director_context: DirectorContext
    warnings: list[PromptDraftWarning] = Field(default_factory=list)
