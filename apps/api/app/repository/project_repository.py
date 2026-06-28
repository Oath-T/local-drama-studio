from collections.abc import Mapping

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.infrastructure.models.project import ProjectRecord


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_projects(self) -> tuple[list[ProjectRecord], int]:
        statement = select(ProjectRecord).order_by(
            ProjectRecord.updated_at.desc(),
            ProjectRecord.created_at.desc(),
            ProjectRecord.id.asc(),
        )
        total = self.session.scalar(select(func.count()).select_from(ProjectRecord)) or 0
        return list(self.session.scalars(statement).all()), total

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self.session.get(ProjectRecord, project_id)

    def create_project(self, project: ProjectRecord) -> ProjectRecord:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def update_project(self, project: ProjectRecord, values: Mapping[str, object]) -> ProjectRecord:
        for key, value in values.items():
            setattr(project, key, value)
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete_project(self, project_id: str) -> None:
        self.session.execute(delete(ProjectRecord).where(ProjectRecord.id == project_id))
        self.session.commit()
