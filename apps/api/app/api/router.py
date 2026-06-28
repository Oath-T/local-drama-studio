from fastapi import APIRouter

from app.api.characters import media_router
from app.api.characters import router as characters_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(characters_router)
api_router.include_router(media_router)
