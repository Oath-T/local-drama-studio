import json
import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.project_canvas import CanvasEdgeData, CanvasNodeData, CanvasViewport
from app.domain.project_canvas import CanvasEdgeType, CanvasNodeType, CanvasViewMode, utc_now
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
    ProjectCanvasRecord,
)
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanvasOutputSyncResult:
    node_id: str
    edge_id: str


class CanvasOutputSyncService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sync_keyframe_run_outputs(self, run_id: str) -> CanvasOutputSyncResult | None:
        run = self.session.get(KeyframeGenerationRunRecord, run_id)
        if run is None:
            return None
        task = self.session.get(KeyframeGenerationTaskRecord, run.keyframe_task_id)
        if task is None:
            return None
        outputs = list(
            self.session.scalars(
                select(KeyframeGenerationOutputRecord)
                .where(KeyframeGenerationOutputRecord.run_id == run.id)
                .order_by(
                    KeyframeGenerationOutputRecord.output_index.asc(),
                    KeyframeGenerationOutputRecord.id.asc(),
                )
            ).all()
        )
        first_result: CanvasOutputSyncResult | None = None
        for output in outputs:
            try:
                purpose_label = "首帧候选" if task.purpose == "first_frame" else "尾帧候选"
                shot_label = task.name.replace("画布快速", "").strip() or "镜头"
                result = self._sync_output(
                    project_id=run.project_id,
                    shot_id=task.shot_id,
                    media_asset_id=output.media_asset_id,
                    output_id=output.id,
                    output_type="keyframe_output",
                    node_type=CanvasNodeType.IMAGE,
                    title=f"{shot_label} · {purpose_label}",
                    temporary_label=purpose_label,
                )
                first_result = first_result or result
            except Exception:
                self.session.rollback()
                logger.warning(
                    "Canvas keyframe output sync failed.",
                    extra={"run_id": run_id, "output_id": output.id},
                    exc_info=True,
                )
        return first_result

    def sync_video_run_outputs(self, run_id: str) -> CanvasOutputSyncResult | None:
        run = self.session.get(VideoGenerationRunRecord, run_id)
        if run is None:
            return None
        task = self.session.get(VideoGenerationTaskRecord, run.video_task_id)
        if task is None:
            return None
        outputs = list(
            self.session.scalars(
                select(VideoGenerationOutputRecord)
                .where(VideoGenerationOutputRecord.run_id == run.id)
                .order_by(
                    VideoGenerationOutputRecord.output_index.asc(),
                    VideoGenerationOutputRecord.id.asc(),
                )
            ).all()
        )
        first_result: CanvasOutputSyncResult | None = None
        for output in outputs:
            try:
                result = self._sync_output(
                    project_id=run.project_id,
                    shot_id=task.shot_id,
                    media_asset_id=output.media_asset_id,
                    output_id=output.id,
                    output_type="video_output",
                    node_type=CanvasNodeType.VIDEO,
                    title=f"{task.name or '镜头'} · 视频候选",
                    temporary_label="视频候选",
                )
                first_result = first_result or result
            except Exception:
                self.session.rollback()
                logger.warning(
                    "Canvas video output sync failed.",
                    extra={"run_id": run_id, "output_id": output.id},
                    exc_info=True,
                )
        return first_result

    def _sync_output(
        self,
        *,
        project_id: str,
        shot_id: str,
        media_asset_id: str,
        output_id: str,
        output_type: str,
        node_type: CanvasNodeType,
        title: str,
        temporary_label: str,
    ) -> CanvasOutputSyncResult | None:
        if self.session.get(ProjectRecord, project_id) is None:
            return None
        shot = self.session.get(ShotRecord, shot_id)
        media_asset = self.session.get(MediaAssetRecord, media_asset_id)
        if shot is None or media_asset is None or media_asset.project_id != project_id:
            return None
        canvas = self._get_or_create_canvas(project_id)
        shot_node = self._get_or_create_node(
            canvas,
            node_type=CanvasNodeType.SHOT,
            entity_type="shot",
            entity_id=shot.id,
            title=shot.name,
            x=160,
            y=80,
        )
        output_node = self._get_or_create_node(
            canvas,
            node_type=node_type,
            entity_type=node_type.value,
            entity_id=media_asset.id,
            title=title,
            x=shot_node.position_x + 340,
            y=shot_node.position_y + 180,
            thumbnail_url=(
                f"/api/media/{media_asset.id}/thumbnail"
                if media_asset.thumbnail_relative_path
                else None
            ),
            temporary_label=temporary_label,
        )
        existing_edge = self._find_generated_edge(canvas.id, output_type, output_id)
        now = utc_now()
        if existing_edge is None:
            existing_edge = ProjectCanvasEdgeRecord(
                id=str(uuid4()),
                canvas_id=canvas.id,
                source_node_id=shot_node.id,
                target_node_id=output_node.id,
                source_handle=None,
                target_handle=None,
                semantic_type=CanvasEdgeType.GENERATED_FROM.value,
                data_json=CanvasEdgeData(
                    status="applied",
                    business_entity_type=output_type,
                    business_entity_id=output_id,
                    applied_at=now,
                    binding_payload={"system": True, "output_id": output_id},
                ).model_dump_json(exclude_none=True),
                created_at=now,
                updated_at=now,
            )
            self.session.add(existing_edge)
            canvas.revision += 1
            canvas.updated_at = now
        self.session.commit()
        return CanvasOutputSyncResult(node_id=output_node.id, edge_id=existing_edge.id)

    def _get_or_create_canvas(self, project_id: str) -> ProjectCanvasRecord:
        canvas = self.session.scalars(
            select(ProjectCanvasRecord).where(ProjectCanvasRecord.project_id == project_id)
        ).first()
        if canvas is not None:
            return canvas
        now = utc_now()
        canvas = ProjectCanvasRecord(
            id=str(uuid4()),
            project_id=project_id,
            view_mode=CanvasViewMode.WORKFLOW.value,
            viewport_json=CanvasViewport().model_dump_json(),
            layout_version=1,
            revision=1,
            created_at=now,
            updated_at=now,
        )
        self.session.add(canvas)
        self.session.flush()
        return canvas

    def _get_or_create_node(
        self,
        canvas: ProjectCanvasRecord,
        *,
        node_type: CanvasNodeType,
        entity_type: str,
        entity_id: str,
        title: str,
        x: float,
        y: float,
        thumbnail_url: str | None = None,
        temporary_label: str | None = None,
    ) -> ProjectCanvasNodeRecord:
        node = self.session.scalars(
            select(ProjectCanvasNodeRecord).where(
                ProjectCanvasNodeRecord.canvas_id == canvas.id,
                ProjectCanvasNodeRecord.entity_type == entity_type,
                ProjectCanvasNodeRecord.entity_id == entity_id,
            )
        ).first()
        if node is not None:
            changed = False
            next_data = CanvasNodeData.model_validate(json.loads(node.data_json or "{}"))
            if title and node.title != title[:120]:
                node.title = title[:120]
                changed = True
            if thumbnail_url and next_data.thumbnail_override != thumbnail_url:
                next_data.thumbnail_override = thumbnail_url
                changed = True
            if temporary_label and next_data.temporary_label != temporary_label:
                next_data.temporary_label = temporary_label
                changed = True
            if changed:
                node.data_json = next_data.model_dump_json(exclude_none=True)
                node.updated_at = utc_now()
                canvas.revision += 1
                canvas.updated_at = node.updated_at
            return node
        now = utc_now()
        data = CanvasNodeData(thumbnail_override=thumbnail_url, temporary_label=temporary_label)
        node = ProjectCanvasNodeRecord(
            id=str(uuid4()),
            canvas_id=canvas.id,
            node_type=node_type.value,
            title=title[:120] or node_type.value,
            position_x=x,
            position_y=y,
            width=240,
            height=150,
            z_index=1000,
            entity_type=entity_type,
            entity_id=entity_id,
            data_json=data.model_dump_json(exclude_none=True),
            created_at=now,
            updated_at=now,
        )
        self.session.add(node)
        canvas.revision += 1
        canvas.updated_at = now
        self.session.flush()
        return node

    def _find_generated_edge(
        self,
        canvas_id: str,
        output_type: str,
        output_id: str,
    ) -> ProjectCanvasEdgeRecord | None:
        edges = self.session.scalars(
            select(ProjectCanvasEdgeRecord).where(
                ProjectCanvasEdgeRecord.canvas_id == canvas_id,
                ProjectCanvasEdgeRecord.semantic_type == CanvasEdgeType.GENERATED_FROM.value,
            )
        ).all()
        for edge in edges:
            try:
                data = json.loads(edge.data_json or "{}")
            except json.JSONDecodeError:
                continue
            if (
                data.get("business_entity_type") == output_type
                and data.get("business_entity_id") == output_id
            ):
                return edge
        return None
