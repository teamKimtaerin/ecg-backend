from fastapi import APIRouter
from .ml import router as ml_router
from .chatbot import router as chatbot_router
from .plugins import router as plugins_router
from .assets import router as assets_router
from .admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")

# /api/v1 prefix로 등록되는 라우터들만 포함
api_router.include_router(ml_router)  # /api/v1/ml
api_router.include_router(chatbot_router)  # /api/v1/chatbot
api_router.include_router(plugins_router)  # /api/v1/plugins
api_router.include_router(assets_router)  # /api/v1/assets
api_router.include_router(admin_router)  # /api/v1/admin
