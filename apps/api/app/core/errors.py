from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

VALIDATION_CODE_MESSAGES: dict[str, str] = {
    "INVALID_ASPECT_RATIO": "请选择有效的画面比例。",
    "INVALID_DEFAULT_LANGUAGE": "请选择有效的默认语言。",
    "INVALID_DEFAULT_FPS": "请选择有效的默认帧率。",
}

HTTP_422 = 422


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def error_response(
    code: str,
    message: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload.model_dump()))


def get_validation_error_code(exc: RequestValidationError) -> tuple[str, str]:
    for error in exc.errors():
        location = error.get("loc", ())
        if len(location) >= 2 and location[0] == "path" and location[1] == "project_id":
            return "INVALID_PROJECT_ID", "项目 ID 格式无效。"

        context = error.get("ctx")
        if isinstance(context, dict):
            raw_error = context.get("error")
            error_text = str(raw_error)
            if error_text in VALIDATION_CODE_MESSAGES:
                return error_text, VALIDATION_CODE_MESSAGES[error_text]

    return "VALIDATION_ERROR", "请求参数校验失败。"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        code, message = get_validation_error_code(exc)
        return error_response(
            code=code,
            message=message,
            status_code=HTTP_422,
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            code="internal_server_error",
            message="An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
