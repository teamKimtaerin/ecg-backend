from fastapi import APIRouter
from .video import router as video_router
from .auth import router as auth_router
from .ml_video import router as ml_video_router
from .render import router as render_router

api_router = APIRouter()

api_router.include_router(video_router)
api_router.include_router(auth_router)
api_router.include_router(ml_video_router)
api_router.include_router(render_router)
