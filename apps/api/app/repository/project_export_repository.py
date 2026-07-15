from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.project_export import ProjectExportRecord


class ProjectExportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def list_exports(self, project_id: str) -> tuple[list[ProjectExportRecord], int]:
        items = list(
            self.session.scalars(
                select(ProjectExportRecord)
                .where(ProjectExportRecord.project_id == project_id)
                .order_by(
                    ProjectExportRecord.created_at.desc(),
                    ProjectExportRecord.id.desc(),
                )
            ).all()
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(ProjectExportRecord)
                .where(ProjectExportRecord.project_id == project_id)
            )
            or 0
        )
        return items, int(total)

    def get_export(self, project_id: str, export_id: str) -> ProjectExportRecord | None:
        return self.session.scalars(
            select(ProjectExportRecord).where(
                ProjectExportRecord.project_id == project_id,
                ProjectExportRecord.id == export_id,
            )
        ).first()

    def get_export_by_id(self, export_id: str) -> ProjectExportRecord | None:
        return self.session.get(ProjectExportRecord, export_id)

    def create_export(self, record: ProjectExportRecord) -> ProjectExportRecord:
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def update_export(self, record: ProjectExportRecord, values: dict[str, object]) -> None:
        try:
            for key, value in values.items():
                setattr(record, key, value)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def complete_with_media(
        self,
        record: ProjectExportRecord,
        media_asset: MediaAssetRecord,
        values: dict[str, object],
    ) -> None:
        try:
            self.session.add(media_asset)
            for key, value in values.items():
                setattr(record, key, value)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def media_assets_by_ids(self, media_asset_ids: list[str]) -> dict[str, MediaAssetRecord]:
        if not media_asset_ids:
            return {}
        records = list(
            self.session.scalars(
                select(MediaAssetRecord).where(
                    MediaAssetRecord.id.in_(sorted(set(media_asset_ids)))
                )
            ).all()
        )
        return {record.id: record for record in records}
