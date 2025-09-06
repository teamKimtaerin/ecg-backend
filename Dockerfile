# =====================================
# Backend Dockerfile (FastAPI)
# =====================================

# ----- Base Stage -----
FROM python:3.11-slim AS base

# 보안 및 성능을 위한 환경변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:$PATH"

WORKDIR /app

# 시스템 의존성 설치 (보안 업데이트 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 보안을 위한 비권한 사용자 생성
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 개발/운영 모드 결정
ARG MODE=dev

# ----- Dev Stage -----
FROM base AS dev

# 개발 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사 및 권한 설정
COPY --chown=appuser:appgroup . .
RUN chmod +x /app

EXPOSE 8000
VOLUME ["/app"]

# 개발환경에서도 보안 고려
USER appuser

# 개발서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ----- Prod Stage -----
FROM base AS prod

# 운영 의존성만 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY --chown=appuser:appgroup . .

# 보안 강화: 실행 권한 최소화
RUN find /app -type f -name "*.py" -exec chmod 644 {} \; \
    && chmod +x /app

EXPOSE 8000

# 비권한 사용자로 실행
USER appuser

# 헬스체크 (애플리케이션별 엔드포인트 사용)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 운영환경: Gunicorn으로 프로덕션 서버 실행
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app.main:app"]