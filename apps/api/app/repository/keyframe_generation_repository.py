from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.keyframe_generation import ACTIVE_RUN_STATUSES
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
    KeyframeGenerationTaskReferenceRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.shot import ShotRecord


@dataclass(frozen=True)
class KeyframeRunListData:
    runs: list[KeyframeGenerationRunRecord]
    outputs_by_run_id: dict[str, list[KeyframeGenerationOutputRecord]]
    media_assets_by_id: dict[str, MediaAssetRecord]
    total: int


class KeyframeGenerationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_task(self, project_id: str, task_id: str) -> KeyframeGenerationTaskRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationTaskRecord).where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.id == task_id,
            )
        ).first()

    def get_shot(self, project_id: str, shot_id: str) -> ShotRecord | None:
        return self.session.scalars(
            select(ShotRecord).where(
                ShotRecord.project_id == project_id,
                ShotRecord.id == shot_id,
            )
        ).first()

    def list_task_references(self, task_id: str) -> list[KeyframeGenerationTaskReferenceRecord]:
        return list(
            self.session.scalars(
                select(KeyframeGenerationTaskReferenceRecord)
                .where(KeyframeGenerationTaskReferenceRecord.task_id == task_id)
                .order_by(
                    KeyframeGenerationTaskReferenceRecord.order_index.asc(),
                    KeyframeGenerationTaskReferenceRecord.created_at.asc(),
                    KeyframeGenerationTaskReferenceRecord.id.asc(),
                )
            ).all()
        )

    def get_media_assets_by_ids(self, ids: list[str]) -> dict[str, MediaAssetRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(MediaAssetRecord).where(MediaAssetRecord.id.in_(ids))
            ).all()
        }

    def get_active_run_for_task(self, task_id: str) -> KeyframeGenerationRunRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationRunRecord)
            .where(
                KeyframeGenerationRunRecord.keyframe_task_id == task_id,
                KeyframeGenerationRunRecord.status.in_(ACTIVE_RUN_STATUSES),
            )
            .order_by(
                KeyframeGenerationRunRecord.created_at.asc(),
                KeyframeGenerationRunRecord.id.asc(),
            )
        ).first()

    def next_run_number(self, task_id: str) -> int:
        current = self.session.scalar(
            select(func.max(KeyframeGenerationRunRecord.run_number)).where(
                KeyframeGenerationRunRecord.keyframe_task_id == task_id
            )
        )
        return int(current or 0) + 1

    def create_run(self, run: KeyframeGenerationRunRecord) -> KeyframeGenerationRunRecord:
        try:
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
            return run
        except Exception:
            self.session.rollback()
            raise

    def get_run(self, project_id: str, run_id: str) -> KeyframeGenerationRunRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationRunRecord).where(
                KeyframeGenerationRunRecord.project_id == project_id,
                KeyframeGenerationRunRecord.id == run_id,
            )
        ).first()

    def get_run_by_id(self, run_id: str) -> KeyframeGenerationRunRecord | None:
        return self.session.get(KeyframeGenerationRunRecord, run_id)

    def list_runs_for_task(self, project_id: str, task_id: str) -> KeyframeRunListData:
        runs = list(
            self.session.scalars(
                select(KeyframeGenerationRunRecord)
                .where(
                    KeyframeGenerationRunRecord.project_id == project_id,
                    KeyframeGenerationRunRecord.keyframe_task_id == task_id,
                )
                .order_by(
                    KeyframeGenerationRunRecord.run_number.desc(),
                    KeyframeGenerationRunRecord.created_at.desc(),
                    KeyframeGenerationRunRecord.id.desc(),
                )
            ).all()
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(KeyframeGenerationRunRecord)
                .where(
                    KeyframeGenerationRunRecord.project_id == project_id,
                    KeyframeGenerationRunRecord.keyframe_task_id == task_id,
                )
            )
            or 0
        )
        outputs_by_run_id = self.list_outputs_for_runs([run.id for run in runs])
        media_assets_by_id = self.get_media_assets_by_ids(
            sorted(
                {
                    output.media_asset_id
                    for outputs in outputs_by_run_id.values()
                    for output in outputs
                }
            )
        )
        return KeyframeRunListData(
            runs=runs,
            outputs_by_run_id=outputs_by_run_id,
            media_assets_by_id=media_assets_by_id,
            total=total,
        )

    def list_outputs_for_runs(
        self, run_ids: list[str]
    ) -> dict[str, list[KeyframeGenerationOutputRecord]]:
        if not run_ids:
            return {}
        outputs = list(
            self.session.scalars(
                select(KeyframeGenerationOutputRecord)
                .where(KeyframeGenerationOutputRecord.run_id.in_(run_ids))
                .order_by(
                    KeyframeGenerationOutputRecord.run_id.asc(),
                    KeyframeGenerationOutputRecord.output_index.asc(),
                    KeyframeGenerationOutputRecord.id.asc(),
                )
            ).all()
        )
        grouped: dict[str, list[KeyframeGenerationOutputRecord]] = {
            run_id: [] for run_id in run_ids
        }
        for output in outputs:
            grouped.setdefault(output.run_id, []).append(output)
        return grouped

    def update_run(self, run: KeyframeGenerationRunRecord, values: dict[str, object]) -> None:
        try:
            for key, value in values.items():
                setattr(run, key, value)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def output_exists(
        self,
        run_id: str,
        provider_filename: str,
        provider_subfolder: str,
        output_index: int,
    ) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(KeyframeGenerationOutputRecord)
                .where(
                    KeyframeGenerationOutputRecord.run_id == run_id,
                    KeyframeGenerationOutputRecord.provider_filename == provider_filename,
                    KeyframeGenerationOutputRecord.provider_subfolder == provider_subfolder,
                    KeyframeGenerationOutputRecord.output_index == output_index,
                )
            )
            or 0
        ) > 0

    def create_output_with_media(
        self,
        media_asset: MediaAssetRecord,
        output: KeyframeGenerationOutputRecord,
    ) -> None:
        try:
            self.session.add(media_asset)
            self.session.add(output)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_output(self, project_id: str, output_id: str) -> KeyframeGenerationOutputRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationOutputRecord).where(
                KeyframeGenerationOutputRecord.project_id == project_id,
                KeyframeGenerationOutputRecord.id == output_id,
            )
        ).first()

    def select_output(self, output: KeyframeGenerationOutputRecord) -> None:
        try:
            run = self.session.get(KeyframeGenerationRunRecord, output.run_id)
            if run is None:
                return
            task_run_ids = list(
                self.session.scalars(
                    select(KeyframeGenerationRunRecord.id).where(
                        KeyframeGenerationRunRecord.keyframe_task_id == run.keyframe_task_id
                    )
                ).all()
            )
            if task_run_ids:
                for record in self.session.scalars(
                    select(KeyframeGenerationOutputRecord).where(
                        KeyframeGenerationOutputRecord.run_id.in_(task_run_ids)
                    )
                ):
                    record.is_selected = False
            output.is_selected = True
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def unselect_output(self, output: KeyframeGenerationOutputRecord) -> None:
        try:
            output.is_selected = False
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def media_asset_for_output(
        self, output: KeyframeGenerationOutputRecord
    ) -> MediaAssetRecord | None:
        return self.session.get(MediaAssetRecord, output.media_asset_id)

    def list_active_runs(self) -> list[KeyframeGenerationRunRecord]:
        try:
            return list(
                self.session.scalars(
                    select(KeyframeGenerationRunRecord)
                    .where(KeyframeGenerationRunRecord.status.in_(ACTIVE_RUN_STATUSES))
                    .order_by(
                        KeyframeGenerationRunRecord.created_at.asc(),
                        KeyframeGenerationRunRecord.id.asc(),
                    )
                ).all()
            )
        except SQLAlchemyError:
            self.session.rollback()
            return []
