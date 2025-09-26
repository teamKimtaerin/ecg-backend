from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.v1.routers import api_router
from app.api.v1.auth import router as auth_router
from app.api.v1.render import router as render_router
from app.api.v1.results import router as results_router
from app.api.v1.projects import router as projects_router
from app.api.v1.ml_video import router as ml_video_router
from app.api.v1.video import router as video_router
from app.core.config import settings
import os
import logging
import time

app = FastAPI(title="HOIT Backend API", version="1.0.0")

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


# CloudFront 프록시 환경에서의 HTTPS 리디렉트 처리를 위한 미들웨어
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

        # HTTPS 리디렉트가 필요한 경우 HTTPS URL로 수정

        # 원본 요청이 HTTPS인지 확인 (CloudFront를 통해 온 경우)
        is_https_request = (
            request.headers.get("x-forwarded-proto") == "https"
            or "cloudfront" in request.headers.get("via", "").lower()
        )

        response = await call_next(request)

        # 307 리디렉트 응답에서 Location 헤더를 HTTPS로 수정
        if (
            response.status_code == 307
            and is_https_request
            and "location" in response.headers
        ):
            location = response.headers["location"]
            if location.startswith("http://"):
                # HTTP를 HTTPS로 변경
                https_location = location.replace("http://", "https://", 1)
                response.headers["location"] = https_location
                logger.info(f"Fixed redirect: {location} -> {https_location}")

        # OAuth 관련 요청에서 세션 쿠키 도메인 설정
        if "/api/auth/google" in str(request.url) and settings.domain:
            set_cookie_header = response.headers.get("set-cookie")
            if set_cookie_header and "session=" in set_cookie_header:
                # 기존 쿠키에서 도메인 설정 추가/수정
                if f"Domain={settings.domain}" not in set_cookie_header:
                    # Domain 파라미터가 없으면 추가
                    new_cookie = set_cookie_header.replace(
                        "samesite=none", f"Domain={settings.domain}; samesite=none"
                    )
                    response.headers["set-cookie"] = new_cookie

        return response


# CloudFront 프록시 미들웨어 추가
app.add_middleware(CloudFrontProxyMiddleware)

# 세션 미들웨어 추가 (OAuth에 필요) - 환경별 최적화
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",  # 인증 토큰 쿠키와 일관성 유지
    https_only=bool(settings.domain),  # 프로덕션에서만 HTTPS 강제
    max_age=3600,  # 1시간
    session_cookie="session",  # 명시적 쿠키 이름
)

# CORS 설정 - 환경변수에서 허용된 origins 읽기
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Production domains
    "https://ho-it.site",
]

# 환경변수가 있으면 그것을 사용, 없으면 기본값 사용
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    # Strip whitespace and filter empty strings
    cors_origins = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
    # Additional validation to remove any malformed entries
    cors_origins = [
        origin for origin in cors_origins if origin.startswith(("http://", "https://"))
    ]
    if not cors_origins:
        logger.warning(
            "No valid CORS origins found in environment variable, using defaults"
        )
        cors_origins = default_origins
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

# API 라우터 등록 - 기존 경로 유지를 위해 별도 등록
app.include_router(auth_router)  # /api/auth
app.include_router(render_router)  # /api/render
app.include_router(results_router)  # /api
app.include_router(projects_router)  # /api/projects
app.include_router(ml_video_router)  # /api/upload-video
app.include_router(video_router)  # /api/upload-video
app.include_router(api_router)  # /api/v1 (assets, ml, admin, plugins, chatbot)


@app.get("/")
async def root():
    return {"message": "HOIT Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "HOIT Backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
