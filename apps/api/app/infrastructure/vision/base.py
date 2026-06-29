from dataclasses import dataclass
from typing import Protocol

from app.api.schemas.vision_analysis import (
    CharacterVisionAnalysisSuggestion,
    SceneVisionAnalysisSuggestion,
)


@dataclass(frozen=True)
class VisionImageInput:
    media_asset_id: str
    original_filename: str
    mime_type: str
    content: bytes


@dataclass(frozen=True)
class CharacterAnalysisContext:
    character_name: str
    look_name: str
    existing_description: str | None


@dataclass(frozen=True)
class SceneAnalysisContext:
    scene_name: str
    state_name: str
    existing_description: str | None


class VisionAnalysisProvider(Protocol):
    async def analyze_character_reference(
        self,
        image: VisionImageInput,
        context: CharacterAnalysisContext,
    ) -> CharacterVisionAnalysisSuggestion: ...

    async def analyze_scene_reference(
        self,
        image: VisionImageInput,
        context: SceneAnalysisContext,
    ) -> SceneVisionAnalysisSuggestion: ...
