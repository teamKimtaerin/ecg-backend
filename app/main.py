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
    # DATABASE_URL이 기본값(로컬)이 아닌 경우만 데이터베이스 초기화 시도
    if not settings.database_url.startswith(
        "postgresql://ecg_user:ecg_password@localhost"
    ):
        try:
            # 데이터베이스 초기화 (테이블 생성 + 시드 데이터)
            from app.db.init_db import init_database

            logger.info("Starting database initialization...")
            init_database()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            # 애플리케이션은 계속 실행 (이미 테이블이 있을 수 있음)
    else:
        logger.info(
            "Skipping database initialization (using default/local database URL)"
        )


# 세션 미들웨어 추가 (OAuth에 필요)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# CORS 설정 - 환경변수에서 허용된 origins 읽기
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
