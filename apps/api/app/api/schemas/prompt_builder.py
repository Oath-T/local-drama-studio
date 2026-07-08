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


class PromptDraftRequest(BaseModel):
    target: PromptDraftTarget = "all"
    style: PromptDraftStyle = "cinematic_short_drama"
    language: PromptDraftLanguage = "en"
    include_negative_prompt: bool = True
    overrides: PromptDraftOverrides | None = None


class PromptDraftWarning(BaseModel):
    code: str
    message: str
    severity: PromptDraftWarningSeverity


class PromptDraftResponse(BaseModel):
    source_shot_updated_at: datetime
    applied_style: PromptDraftStyle
    context_summary_zh: str
    first_frame_prompt_en: str
    end_frame_prompt_en: str
    motion_prompt_en: str
    negative_prompt_en: str
    camera_motion: str | None
    warnings: list[PromptDraftWarning] = Field(default_factory=list)
