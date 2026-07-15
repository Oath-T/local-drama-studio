from pydantic import BaseModel, Field


class TimelineProjectSpec(BaseModel):
    aspect_ratio: str
    default_fps: int


class TimelineFfmpegStatus(BaseModel):
    available: bool
    ffprobe_available: bool
    message: str | None = None


class TimelineBlocker(BaseModel):
    code: str
    shot_id: str | None = None
    message: str


class TimelineClipResponse(BaseModel):
    shot_id: str
    shot_order: int
    shot_name: str
    status: str
    adopted_video_output_id: str | None
    media_asset_id: str | None
    content_url: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: int | None
    warnings: list[str] = Field(default_factory=list)


class ProjectTimelineResponse(BaseModel):
    project_id: str
    exportable: bool
    total_shots: int
    ready_clip_count: int
    missing_clip_count: int
    estimated_duration_seconds: float
    project_spec: TimelineProjectSpec
    ffmpeg: TimelineFfmpegStatus
    clips: list[TimelineClipResponse]
    blockers: list[TimelineBlocker]
