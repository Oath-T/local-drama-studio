import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.infrastructure.database import initialize_database
from app.service.keyframe_generation_runner import recover_active_keyframe_runs
from app.service.video_generation_runner import recover_active_video_runs
from app.service.vision_analysis_task_runner import mark_interrupted_vision_tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    mark_interrupted_vision_tasks()
    app.state.keyframe_recovery_task = asyncio.create_task(recover_active_keyframe_runs())
    app.state.video_recovery_task = asyncio.create_task(recover_active_video_runs())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
