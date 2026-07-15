from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.character import MediaAssetResponse


class ProjectExportCreateRequest(BaseModel):
    name: str | None = "最终成片导出"
    target_width: int
    target_height: int
    target_fps: int
    video_codec: str = "libx264"


class ProjectExportResponse(BaseModel):
    id: str
    project_id: str
    name: str
    status: str
    progress_percent: int
    current_stage: str
    clip_count: int
    duration_seconds: float | None
    target_width: int
    target_height: int
    target_fps: int
    video_codec: str
    output_format: str
    error_message: str | None
    output_media_asset_id: str | None
    output_media_asset: MediaAssetResponse | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ProjectExportListResponse(BaseModel):
    items: list[ProjectExportResponse]
    total: int


class ProjectExportStartResponse(BaseModel):
    id: str
    status: str
    progress_percent: int
    current_stage: str
