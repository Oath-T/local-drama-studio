from dataclasses import dataclass


@dataclass(frozen=True)
class PromptStylePreset:
    style: str
    frame_fragment: str
    motion_fragment: str


STYLE_PRESETS: dict[str, PromptStylePreset] = {
    "cinematic_short_drama": PromptStylePreset(
        style="cinematic_short_drama",
        frame_fragment="realistic cinematic short drama style, vertical 9:16, live-action look",
        motion_fragment="smooth cinematic short drama motion, stable vertical framing",
    ),
    "ultra_realistic": PromptStylePreset(
        style="ultra_realistic",
        frame_fragment=(
            "ultra realistic live-action detail, natural skin texture, cinematic lighting"
        ),
        motion_fragment="natural realistic motion, stable facial continuity, no stylized animation",
    ),
    "rain_night_neon": PromptStylePreset(
        style="rain_night_neon",
        frame_fragment="rainy night neon atmosphere, wet reflections, blue and magenta city light",
        motion_fragment="falling rain, shimmering neon reflections, slow moody camera movement",
    ),
    "office_drama": PromptStylePreset(
        style="office_drama",
        frame_fragment=(
            "tense office drama atmosphere, restrained production design, oppressive mood"
        ),
        motion_fragment="controlled office drama pacing, subtle tension, restrained camera motion",
    ),
    "emotional_closeup": PromptStylePreset(
        style="emotional_closeup",
        frame_fragment="emotional close-up emphasis, expressive eyes, shallow depth of field",
        motion_fragment=(
            "subtle facial expression change, intimate close-up motion, emotional tension"
        ),
    ),
    "action_tension": PromptStylePreset(
        style="action_tension",
        frame_fragment="high tension action drama style, dynamic blocking, urgent visual energy",
        motion_fragment="tense physical movement, dynamic camera tension, smooth action continuity",
    ),
}


def get_style_preset(style: str) -> PromptStylePreset:
    return STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic_short_drama"])
