from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.routers import api_router
from app.core.config import settings
import os
import logging

app = FastAPI(title="ECG Backend API", version="1.0.0")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    # 테스트 모드에서는 데이터베이스 초기화 건너뛰기
    if os.getenv("MODE") == "test":
        logger.info("Skipping database initialization for testing mode")
        return

    # 프로덕션 환경에서 DB 초기화
    logger.info("Starting database initialization...")
    try:
        from app.db.init_db import init_database
        init_database()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        # 프로덕션에서는 DB 초기화 실패 시에도 서버 시작을 허용
        # (이미 초기화된 DB일 수 있음)


# 세션 미들웨어 추가 (OAuth에 필요)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# CORS 설정 - 환경변수에서 허용된 origins 읽기
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Production domains
    "https://ecg-frontend.vercel.app",
    "https://ecg-project.com"
]

# 환경변수가 있으면 그것을 사용, 없으면 기본값 사용
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    cors_origins = cors_origins_env.split(",")
else:
    cors_origins = default_origins

# 개발 환경에서는 모든 origin 허용 옵션
if os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true":
    cors_origins = ["*"]

logger.info(f"CORS Origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # 모든 헤더를 프론트엔드에 노출
)

# API 라우터 등록
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "ECG Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ECG Backend"}


@app.get("/api/test")
async def test_endpoint():
    return {"data": "ECG Backend Test", "demo_mode": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
