from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PromptDraftTarget = Literal["keyframe", "video", "all"]
PromptDraftStyle = Literal["cinematic_short_drama"]
PromptDraftLanguage = Literal["en"]
PromptDraftWarningSeverity = Literal["info", "warning"]


class PromptDraftRequest(BaseModel):
    target: PromptDraftTarget = "all"
    style: PromptDraftStyle = "cinematic_short_drama"
    language: PromptDraftLanguage = "en"
    include_negative_prompt: bool = True


class PromptDraftWarning(BaseModel):
    code: str
    message: str
    severity: PromptDraftWarningSeverity


class PromptDraftResponse(BaseModel):
    source_shot_updated_at: datetime
    context_summary_zh: str
    first_frame_prompt_en: str
    end_frame_prompt_en: str
    motion_prompt_en: str
    negative_prompt_en: str
    camera_motion: str | None
    warnings: list[PromptDraftWarning] = Field(default_factory=list)
