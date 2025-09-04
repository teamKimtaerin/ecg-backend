from fastapi import APIRouter
from .video import router as video_router

api_router = APIRouter()

api_router.include_router(video_router)
