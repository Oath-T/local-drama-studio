from fastapi import APIRouter

from app.api.asset_picker import router as asset_picker_router
from app.api.asset_summaries import router as asset_summaries_router
from app.api.characters import media_router
from app.api.characters import router as characters_router
from app.api.generation_tasks import router as generation_tasks_router
from app.api.health import router as health_router
from app.api.keyframe_generation import router as keyframe_generation_router
from app.api.keyframe_tasks import router as keyframe_tasks_router
from app.api.production_status import router as production_status_router
from app.api.project_canvas import router as project_canvas_router
from app.api.project_exports import router as project_exports_router
from app.api.project_timeline import router as project_timeline_router
from app.api.projects import router as projects_router
from app.api.prompt_builder import router as prompt_builder_router
from app.api.scenes import router as scenes_router
from app.api.shot_recommendations import router as shot_recommendations_router
from app.api.shots import router as shots_router
from app.api.system import router as system_router
from app.api.video_generation import router as video_generation_router
from app.api.vision_analysis import router as vision_analysis_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(characters_router)
api_router.include_router(scenes_router)
api_router.include_router(shots_router)
api_router.include_router(prompt_builder_router)
api_router.include_router(asset_summaries_router)
api_router.include_router(asset_picker_router)
api_router.include_router(keyframe_tasks_router)
api_router.include_router(keyframe_generation_router)
api_router.include_router(video_generation_router)
api_router.include_router(generation_tasks_router)
api_router.include_router(production_status_router)
api_router.include_router(project_canvas_router)
api_router.include_router(project_timeline_router)
api_router.include_router(project_exports_router)
api_router.include_router(shot_recommendations_router)
api_router.include_router(vision_analysis_router)
api_router.include_router(system_router)
api_router.include_router(media_router)
