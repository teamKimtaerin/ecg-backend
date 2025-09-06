from fastapi import APIRouter
from .video import router as video_router
from .auth import router as auth_router

api_router = APIRouter()

api_router.include_router(video_router)
api_router.include_router(auth_router)
