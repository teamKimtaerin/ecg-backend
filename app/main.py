from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.v1.routers import api_router
from app.core.config import settings
import os
import logging
import time

app = FastAPI(title="ECG Backend API", version="1.0.0")

# Rate limiting 설정
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 요청 로깅 미들웨어
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 요청 정보 로깅 (특히 OAuth 콜백 관련)
        client_ip = request.headers.get(
            "x-forwarded-for", request.client.host if request.client else "unknown"
        )
        user_agent = request.headers.get("user-agent", "unknown")

        if "/api/auth/google" in str(request.url):
            logger.info(f"🔵 OAuth Request: {request.method} {request.url}")
            logger.info(f"🔵 Client IP: {client_ip}")
            logger.info(f"🔵 User-Agent: {user_agent}")
            logger.info(f"🔵 Headers: {dict(request.headers)}")

        # 응답 처리
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            if "/api/auth/google" in str(request.url):
                logger.info(
                    f"🟢 OAuth Response: {response.status_code} - {process_time:.3f}s"
                )

            return response
        except Exception as e:
            process_time = time.time() - start_time

            if "/api/auth/google" in str(request.url):
                logger.error(f"🔴 OAuth Error: {str(e)} - {process_time:.3f}s")
                logger.error(f"🔴 Exception type: {type(e)}")
                import traceback

                logger.error(f"🔴 Traceback: {traceback.format_exc()}")

            raise


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

    # 좀비 Job 정리 로직
    logger.info("Starting zombie job cleanup...")
    try:
        from app.db.database import get_db
        from app.models.job import Job, JobStatus
        from datetime import datetime, timedelta

        db = next(get_db())

        # 30분 이상 처리 중인 작업 찾기
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        zombie_jobs = (
            db.query(Job)
            .filter(Job.status == JobStatus.PROCESSING, Job.updated_at < cutoff_time)
            .all()
        )

        zombie_count = len(zombie_jobs)
        if zombie_count > 0:
            # 좀비 작업들을 실패로 변경
            for job in zombie_jobs:
                job.status = JobStatus.FAILED
                job.error_message = "Processing timeout - server restart detected"

            db.commit()
            logger.info(f"Cleaned up {zombie_count} zombie jobs")
        else:
            logger.info("No zombie jobs found")

    except Exception as e:
        logger.error(f"Zombie job cleanup failed: {str(e)}")
        # 좀비 정리 실패는 서버 시작을 막지 않음
    finally:
        if "db" in locals():
            db.close()


# 요청 로깅 미들웨어 추가 (가장 먼저)
app.add_middleware(RequestLoggingMiddleware)


# CloudFront 프록시 환경에서의 OAuth 세션 처리를 위한 미들웨어
class CloudFrontProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # CloudFront 프록시 헤더 정보를 사용해 실제 스키마와 호스트 설정
        if "cloudfront" in request.headers.get("via", "").lower():
            # CloudFront를 통한 요청인 경우
            forwarded_proto = request.headers.get("x-forwarded-proto", "https")
            forwarded_host = request.headers.get("host", "")

            # URL을 재구성하여 올바른 스키마 사용
            if forwarded_proto == "http" and "cloudfront.net" in forwarded_host:
                # CloudFront에서 오는 HTTP 요청을 HTTPS로 처리
                new_url = str(request.url).replace("http://", "https://")
                request._url = new_url

        response = await call_next(request)
        return response


# CloudFront 프록시 미들웨어 추가
app.add_middleware(CloudFrontProxyMiddleware)

# 세션 미들웨어 추가 (OAuth에 필요) - CloudFront 환경 최적화
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="none",  # CloudFront 크로스 도메인 허용
    https_only=False,  # CloudFront 내부 HTTP 프록시 허용
    max_age=3600,  # 1시간
    session_cookie="session",  # 명시적 쿠키 이름
)

# CORS 설정 - 환경변수에서 허용된 origins 읽기
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Production domains
    "https://ecg-frontend.vercel.app",
    "https://ecg-project.com",
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
    expose_headers=["*"],  # 모든 헤더를 프론트엔드에 노출
)

# API 라우터 등록
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "ECG Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ECG Backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
