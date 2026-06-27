from uuid import UUID, uuid4

from fastapi import status

from app.api.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.core.errors import AppError
from app.domain.project import (
    ProjectErrorCode,
    ensure_utc,
    normalize_nullable_text,
    normalize_required_name,
    utc_now,
)
from app.infrastructure.models.project import ProjectRecord
from app.repository.project_repository import ProjectRepository

PROJECT_ERROR_MESSAGES: dict[ProjectErrorCode, str] = {
    ProjectErrorCode.NOT_FOUND: "项目不存在或已被删除。",
    ProjectErrorCode.NAME_REQUIRED: "请输入项目名称。",
    ProjectErrorCode.NAME_TOO_LONG: "项目名称不能超过 100 个字符。",
    ProjectErrorCode.DESCRIPTION_TOO_LONG: "项目简介不能超过 1000 个字符。",
    ProjectErrorCode.STYLE_TOO_LONG: "默认视觉风格不能超过 200 个字符。",
    ProjectErrorCode.INVALID_ASPECT_RATIO: "请选择有效的画面比例。",
    ProjectErrorCode.INVALID_DEFAULT_LANGUAGE: "请选择有效的默认语言。",
    ProjectErrorCode.INVALID_DEFAULT_FPS: "请选择有效的默认帧率。",
    ProjectErrorCode.INVALID_ID: "项目 ID 格式无效。",
}

HTTP_422 = 422


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def list_projects(self) -> tuple[list[ProjectRecord], int]:
        projects, total = self.repository.list_projects()
        for project in projects:
            self._normalize_project_datetimes(project)
        return projects, total

    def get_project(self, project_id: UUID) -> ProjectRecord:
        project = self.repository.get_project(str(project_id))
        if project is None:
            raise_project_error(ProjectErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND)
        self._normalize_project_datetimes(project)
        return project

    def create_project(self, payload: ProjectCreateRequest) -> ProjectRecord:
        now = utc_now()
        project = ProjectRecord(
            id=str(uuid4()),
            name=self._normalize_name(payload.name),
            description=self._normalize_nullable(
                payload.description,
                1000,
                ProjectErrorCode.DESCRIPTION_TOO_LONG,
            ),
            aspect_ratio=payload.aspect_ratio,
            default_style=self._normalize_nullable(
                payload.default_style,
                200,
                ProjectErrorCode.STYLE_TOO_LONG,
            ),
            default_language=payload.default_language,
            default_fps=payload.default_fps,
            cover_image_path=None,
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_project(project)
        self._normalize_project_datetimes(created)
        return created

    def update_project(self, project_id: UUID, payload: ProjectUpdateRequest) -> ProjectRecord:
        project = self.repository.get_project(str(project_id))
        if project is None:
            raise_project_error(ProjectErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND)

        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}

        if "name" in submitted:
            values["name"] = self._normalize_name(submitted["name"])
        if "description" in submitted:
            values["description"] = self._normalize_nullable(
                submitted["description"],
                1000,
                ProjectErrorCode.DESCRIPTION_TOO_LONG,
            )
        if "aspect_ratio" in submitted:
            values["aspect_ratio"] = submitted["aspect_ratio"]
        if "default_style" in submitted:
            values["default_style"] = self._normalize_nullable(
                submitted["default_style"],
                200,
                ProjectErrorCode.STYLE_TOO_LONG,
            )
        if "default_language" in submitted:
            values["default_language"] = submitted["default_language"]
        if "default_fps" in submitted:
            values["default_fps"] = submitted["default_fps"]

        values["updated_at"] = utc_now()
        updated = self.repository.update_project(project, values)
        self._normalize_project_datetimes(updated)
        return updated

    def delete_project(self, project_id: UUID) -> None:
        project = self.repository.get_project(str(project_id))
        if project is None:
            raise_project_error(ProjectErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND)
        self.repository.delete_project(str(project_id))

    @staticmethod
    def _normalize_name(value: object) -> str:
        try:
            return normalize_required_name(value if isinstance(value, str) else None)
        except ValueError as exc:
            code = exc.args[0] if exc.args else ProjectErrorCode.NAME_REQUIRED
            raise_project_error(ProjectErrorCode(code), HTTP_422)

    @staticmethod
    def _normalize_nullable(
        value: object,
        max_length: int,
        error_code: ProjectErrorCode,
    ) -> str | None:
        try:
            return normalize_nullable_text(value if isinstance(value, str) else None, max_length)
        except ValueError:
            raise_project_error(error_code, HTTP_422)

    @staticmethod
    def _normalize_project_datetimes(project: ProjectRecord) -> None:
        project.created_at = ensure_utc(project.created_at)
        project.updated_at = ensure_utc(project.updated_at)


def raise_project_error(code: ProjectErrorCode, http_status: int) -> None:
    raise AppError(
        code=code.value,
        message=PROJECT_ERROR_MESSAGES[code],
        status_code=http_status,
    )
