from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.models.character import CharacterRecord, MediaAssetRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
    ProjectCanvasRecord,
)
from app.infrastructure.models.project_export import ProjectExportRecord
from app.infrastructure.models.scene import SceneRecord
from app.infrastructure.models.shot import ShotRecord


class ProjectCanvasRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_canvas(self, project_id: str) -> ProjectCanvasRecord | None:
        return self.session.scalars(
            select(ProjectCanvasRecord)
            .where(ProjectCanvasRecord.project_id == project_id)
            .options(
                selectinload(ProjectCanvasRecord.nodes),
                selectinload(ProjectCanvasRecord.edges),
            )
        ).first()

    def get_canvas_by_id(self, canvas_id: str) -> ProjectCanvasRecord | None:
        return self.session.scalars(
            select(ProjectCanvasRecord)
            .where(ProjectCanvasRecord.id == canvas_id)
            .options(
                selectinload(ProjectCanvasRecord.nodes),
                selectinload(ProjectCanvasRecord.edges),
            )
        ).first()

    def get_node(self, canvas_id: str, node_id: str) -> ProjectCanvasNodeRecord | None:
        return self.session.scalars(
            select(ProjectCanvasNodeRecord).where(
                ProjectCanvasNodeRecord.canvas_id == canvas_id,
                ProjectCanvasNodeRecord.id == node_id,
            )
        ).first()

    def get_edge(self, canvas_id: str, edge_id: str) -> ProjectCanvasEdgeRecord | None:
        return self.session.scalars(
            select(ProjectCanvasEdgeRecord).where(
                ProjectCanvasEdgeRecord.canvas_id == canvas_id,
                ProjectCanvasEdgeRecord.id == edge_id,
            )
        ).first()

    def add(self, record: object) -> None:
        self.session.add(record)

    def delete_node(self, record: ProjectCanvasNodeRecord) -> None:
        self.session.delete(record)

    def delete_edge(self, record: ProjectCanvasEdgeRecord) -> None:
        self.session.delete(record)

    def clear_canvas(self, canvas_id: str) -> None:
        self.session.execute(
            delete(ProjectCanvasEdgeRecord).where(ProjectCanvasEdgeRecord.canvas_id == canvas_id)
        )
        self.session.execute(
            delete(ProjectCanvasNodeRecord).where(ProjectCanvasNodeRecord.canvas_id == canvas_id)
        )

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def refresh(self, record: object) -> None:
        self.session.refresh(record)

    def entity_belongs_to_project(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
    ) -> bool:
        model_by_type = {
            "character": CharacterRecord,
            "scene": SceneRecord,
            "shot": ShotRecord,
            "image": MediaAssetRecord,
            "video": MediaAssetRecord,
            "export": ProjectExportRecord,
        }
        model = model_by_type.get(entity_type)
        if model is None:
            return False
        record = self.session.get(model, entity_id)
        if record is None or getattr(record, "project_id", None) != project_id:
            return False
        if entity_type in {"image", "video"}:
            return getattr(record, "media_type", None) == entity_type
        return True

    def entity_counts(self, project_id: str) -> tuple[int, int, int]:
        character_count = self.session.scalar(
            select(func.count())
            .select_from(CharacterRecord)
            .where(CharacterRecord.project_id == project_id)
        )
        scene_count = self.session.scalar(
            select(func.count())
            .select_from(SceneRecord)
            .where(SceneRecord.project_id == project_id)
        )
        shot_count = self.session.scalar(
            select(func.count()).select_from(ShotRecord).where(ShotRecord.project_id == project_id)
        )
        return int(character_count or 0), int(scene_count or 0), int(shot_count or 0)

    def list_entities_for_batch(
        self, project_id: str
    ) -> tuple[list[CharacterRecord], list[SceneRecord], list[ShotRecord]]:
        characters = list(
            self.session.scalars(
                select(CharacterRecord)
                .where(CharacterRecord.project_id == project_id)
                .order_by(CharacterRecord.created_at.asc(), CharacterRecord.id.asc())
            ).all()
        )
        scenes = list(
            self.session.scalars(
                select(SceneRecord)
                .where(SceneRecord.project_id == project_id)
                .order_by(SceneRecord.created_at.asc(), SceneRecord.id.asc())
            ).all()
        )
        shots = list(
            self.session.scalars(
                select(ShotRecord)
                .where(ShotRecord.project_id == project_id)
                .order_by(ShotRecord.order_index.asc(), ShotRecord.id.asc())
            ).all()
        )
        return characters, scenes, shots
