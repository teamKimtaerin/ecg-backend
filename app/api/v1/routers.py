from fastapi import APIRouter
from .video import router as video_router
from .auth import router as auth_router
from .ml_video import router as ml_video_router
from .ml import router as ml_router
from .results import router as results_router
from .projects import router as projects_router
from .render import router as render_router
from .assets import router as assets_router


api_router = APIRouter()

api_router.include_router(video_router)
api_router.include_router(auth_router)
api_router.include_router(ml_video_router)
api_router.include_router(ml_router)
api_router.include_router(results_router)
api_router.include_router(projects_router)
api_router.include_router(render_router)
api_router.include_router(assets_router)
