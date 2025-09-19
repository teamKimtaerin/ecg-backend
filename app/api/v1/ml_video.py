"""
ML 서버와의 통신을 위한 비디오 처리 API

EC2 ML 서버로부터 분석 결과를 받고, 비디오 처리 요청을 관리합니다.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional, Union
from enum import Enum
import asyncio
import logging
import aiohttp
import hashlib
import hmac
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.job_service import JobService
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.schemas.user import UserResponse

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload-video", tags=["ml-video"])
limiter = Limiter(key_func=get_remote_address)


def verify_hmac_signature(request_body: bytes, signature: str, secret_key: str) -> bool:
    """
    HMAC 서명을 검증하는 함수
    """
    try:
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), request_body, hashlib.sha256
        ).hexdigest()

        # 시간 공격을 방지하기 위한 안전한 비교
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        logger.error(f"HMAC verification failed: {str(e)}")
        return False


def normalize_timestamp_fields(
    data: Union[Dict[str, Any], Any]
) -> Union[Dict[str, Any], Any]:
    """
    ML 서버와 WhisperX의 서로 다른 타임스탬프 필드명을 통일

    ML 서버: start_time, end_time
    WhisperX/Backend: start, end

    모든 타임스탬프 필드를 start, end로 통일
    """
    if isinstance(data, dict):
        # start_time -> start 변환
        if "start_time" in data and "start" not in data:
            data["start"] = data.pop("start_time")
        elif "start_time" in data:
            # 둘 다 있으면 start_time 제거
            data.pop("start_time")

        # end_time -> end 변환
        if "end_time" in data and "end" not in data:
            data["end"] = data.pop("end_time")
        elif "end_time" in data:
            # 둘 다 있으면 end_time 제거
            data.pop("end_time")

        # 중첩된 구조 재귀 처리
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (dict, list)):
                        normalize_timestamp_fields(item)
            elif isinstance(value, dict):
                normalize_timestamp_fields(value)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                normalize_timestamp_fields(item)

    return data


# Pydantic 모델들
class ProcessingStatus(Enum):
    """처리 상태"""

    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MLResultRequest(BaseModel):
    """ML 서버로부터 받는 결과 요청 (Webhook Input)"""

    job_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class MLResultResponse(BaseModel):
    """ML 서버 콜백 처리 응답"""

    status: str
    reason: Optional[str] = None


class ClientProcessRequest(BaseModel):
    """클라이언트로부터 받는 비디오 처리 요청"""

    fileKey: str
    language: Optional[str] = None  # 언어 코드 (선택적, 없으면 자동 감지)


class VideoProcessRequest(BaseModel):
    """ML 서버로 보내는 비디오 처리 요청"""

    job_id: str
    video_url: str
    language: Optional[str] = None  # 언어 코드


class ClientProcessResponse(BaseModel):
    """클라이언트에게 보내는 비디오 처리 응답"""

    message: str
    job_id: str


class VideoProcessResponse(BaseModel):
    """ML 서버 비디오 처리 응답"""

    job_id: str
    status: str
    message: str
    status_url: str
    estimated_time: Optional[int] = None  # 예상 처리 시간 (초)


class JobStatusResponse(BaseModel):
    """작업 상태 응답 (기존 엔드포인트용)"""

    job_id: str
    status: str
    progress: float
    created_at: str
    last_updated: Optional[str] = None
    current_message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# PostgreSQL 기반 작업 상태 관리 (메모리 저장소에서 마이그레이션됨)

# 환경변수에서 ML 서버 설정 읽기
MODEL_SERVER_URL = settings.MODEL_SERVER_URL
FASTAPI_BASE_URL = settings.FASTAPI_BASE_URL
ML_API_TIMEOUT = settings.ML_API_TIMEOUT


@router.post("/request-process", response_model=ClientProcessResponse)
@limiter.limit("5/minute")
async def request_process(
    request: Request,
    data: ClientProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    클라이언트로부터 비디오 처리 요청을 받아 ML 서버로 전달
    """

    try:
        # 입력 검증
        if not data.fileKey:
            raise HTTPException(status_code=400, detail="fileKey는 필수입니다")

        # job_id 생성
        import uuid

        job_id = str(uuid.uuid4())

        # S3 URL 생성
        import os

        s3_bucket_name = os.getenv("S3_BUCKET_NAME", "default-bucket")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        video_url = (
            f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{data.fileKey}"
        )

        # PostgreSQL에 작업 생성
        job_service = JobService(db)
        job_service.create_job(
            job_id=job_id,
            status="processing",
            progress=0,
            video_url=video_url,
            file_key=data.fileKey,
        )

        logger.info(f"새 비디오 처리 요청 - Job ID: {job_id}")

        # VideoProcessRequest 객체 생성
        video_request = VideoProcessRequest(
            job_id=job_id,
            video_url=video_url,
            language=data.language or "auto",  # 없으면 자동 감지
        )

        # 백그라운드에서 EC2 ML 서버에 요청 전송 (DB 세션 전달)
        background_tasks.add_task(trigger_ml_server, job_id, video_request, db)

        return ClientProcessResponse(message="Video processing started.", job_id=job_id)

    except Exception as e:
        logger.error(f"클라이언트 비디오 처리 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"요청 처리 실패: {str(e)}")


# /process-video 엔드포인트는 제거됨 (내부용으로 더 이상 필요하지 않음)
# 모든 비디오 처리는 /request-process를 통해 진행


@router.post("/result", response_model=MLResultResponse)
async def receive_ml_results(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    ⚠️  ML 서버 전용 Webhook 엔드포인트 ⚠️

    이 엔드포인트는 ML 서버가 비디오 처리 결과를 콜백할 때 사용합니다.
    클라이언트/프론트엔드는 이 엔드포인트를 사용하면 안 됩니다!

    📢 클라이언트는 GET /api/upload-video/status/{job_id} 를 사용하세요!

    ML 서버가 호출하는 엔드포인트:
    POST http://fastapi-backend:8000/api/upload-video/result

    Required fields in request body (MLResultRequest):
    - job_id: str (required)
    - status: str (required) - one of: "processing", "completed", "failed"
    - progress: int (optional) - 0-100
    - message: str (optional)
    - result: dict (optional) - final results when status="completed"
    - error_message: str (optional) - error details when status="failed"
    """

    try:
        # 원본 요청 바디 읽기 (HMAC 검증용)
        request_body = await request.body()

        # HMAC 서명 검증 (선택적 - 환경변수로 활성화)
        signature_header = request.headers.get("X-Signature-256", "")
        webhook_secret = (
            getattr(settings, "webhook_secret_key", None) or settings.secret_key
        )

        if signature_header and webhook_secret:
            if not verify_hmac_signature(
                request_body, signature_header, webhook_secret
            ):
                logger.warning(
                    f"HMAC signature verification failed from IP: {request.client.host}"
                )
                raise HTTPException(status_code=401, detail="Invalid signature")
        elif signature_header:
            logger.warning("HMAC signature provided but no webhook secret configured")

        # 요청 정보 로깅
        client_ip = request.client.host
        content_type = request.headers.get("content-type", "unknown")
        user_agent = request.headers.get("user-agent", "unknown")
        body_text = request_body.decode("utf-8") if request_body else "empty"

        logger.info(
            f"ML 콜백 수신 - Client: {client_ip}, Content-Type: {content_type}, "
            f"User-Agent: {user_agent}, Body: {body_text[:200]}..."
        )

        # JSON 파싱 및 검증
        try:
            import json

            body_json = json.loads(body_text) if body_text != "empty" else {}
            ml_result = MLResultRequest(**body_json)
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON 파싱 실패 - Client: {client_ip}, Error: {str(e)}, Body: {body_text}"
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Invalid JSON format",
                    "message": str(e),
                    "received_body": body_text[:500],
                },
            )
        except ValidationError as e:
            logger.error(
                f"요청 데이터 검증 실패 - Client: {client_ip}, "
                f"Validation Errors: {e.errors()}, Body: {body_text}"
            )

            # 프론트엔드의 잘못된 요청 감지 (User-Agent: node)
            if user_agent == "node" or "status" in str(e.errors()[0].get("loc", [])):
                error_detail = {
                    "error": "⚠️ Frontend API Misuse Detected - Wrong Endpoint!",
                    "message": "🚨 이 엔드포인트는 ML 서버 전용입니다! 클라이언트는 사용할 수 없습니다.",
                    "correct_endpoint": "GET /api/upload-video/status/{job_id}",
                    "wrong_endpoint": "POST /api/upload-video/result (ML Server Webhook Only)",
                    "bug_report_analysis": {
                        "issue": "Request/Response 스키마 혼동이 아님",
                        "reality": "MLResultRequest는 ML 서버 콜백용으로 정확함",
                        "solution": "프론트엔드는 GET /status/{job_id} 사용 필요",
                    },
                    "fix_required": {
                        "1_change_method": "POST → GET",
                        "2_change_endpoint": "/api/upload-video/result → /api/upload-video/status/{job_id}",
                        "3_remove_body": "요청 본문 제거 (GET 요청)",
                        "4_status_field": "status 필드는 ML 서버가 보내는 것이 맞음",
                    },
                    "example_correct_usage": {
                        "url": "http://localhost:8000/api/upload-video/status/your-job-id",
                        "method": "GET",
                        "headers": {"Content-Type": "application/json"},
                    },
                    "documentation": "/docs/FRONTEND_CRITICAL_FIX.md",
                    "validation_errors": e.errors(),
                    "received_body": body_text[:500],
                }
            else:
                error_detail = {
                    "error": "Invalid request format",
                    "validation_errors": e.errors(),
                    "received_body": body_text[:500],
                    "expected_format": {
                        "job_id": "string (required)",
                        "status": "string (required)",
                        "progress": "integer (optional)",
                        "message": "string (optional)",
                        "result": "object (optional)",
                        "error_message": "string (optional)",
                    },
                }

            raise HTTPException(status_code=422, detail=error_detail)

        job_id = ml_result.job_id

        logger.info(
            f"ML 결과 수신 - Job ID: {job_id}, Status: {ml_result.status}, "
            f"Progress: {ml_result.progress}, Client: {client_ip}"
        )
        # ML 서버 결과 데이터의 타임스탬프 필드명 정규화
        if ml_result.result:
            try:
                ml_result.result = normalize_timestamp_fields(ml_result.result)
                logger.debug(f"타임스탬프 필드 정규화 완료 - Job ID: {job_id}")
            except Exception as e:
                logger.warning(f"타임스탬프 필드 정규화 실패 - Job ID: {job_id}, Error: {str(e)}")

        # PostgreSQL에서 작업 상태 업데이트
        job_service = JobService(db)

        # 작업이 존재하는지 확인
        job = job_service.get_job(job_id)
        if not job:
            logger.warning(f"존재하지 않는 Job ID: {job_id}, Client: {client_ip}")
            raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

        # 멱등성 보장: 이미 완료된 작업에 대한 요청은 조용히 성공 처리
        if job.status == "completed" and ml_result.status in [
            "completed",
            "processing",
        ]:
            logger.info(
                f"멱등성 처리 - 이미 완료된 작업에 대한 콜백: Job ID: {job_id}, "
                f"Current Status: {job.status}, New Status: {ml_result.status}"
            )
            return MLResultResponse(status="already_completed")

        if job.status == "failed" and ml_result.status != "failed":
            logger.info(
                f"멱등성 처리 - 이미 실패한 작업에 대한 콜백: Job ID: {job_id}, "
                f"Current Status: {job.status}, New Status: {ml_result.status}"
            )
            return MLResultResponse(status="already_failed")

        # 트랜잭션으로 상태 업데이트 처리
        try:
            if ml_result.status == "processing":
                # 진행 상황 업데이트 (message는 로그로만 기록)
                success = job_service.update_job_status(
                    job_id=job_id, status="processing", progress=ml_result.progress or 0
                )
                logger.info(
                    f"진행 상황 업데이트 - Job ID: {job_id}, Progress: {ml_result.progress}%, Message: {ml_result.message}"
                )

            elif ml_result.status in ["completed", "failed"]:
                # 최종 결과 처리
                final_status = (
                    "completed" if ml_result.status == "completed" else "failed"
                )
                success = job_service.update_job_status(
                    job_id=job_id,
                    status=final_status,
                    progress=100 if final_status == "completed" else job.progress,
                    result=ml_result.result,
                    error_message=ml_result.error_message,
                )

                if final_status == "completed":
                    logger.info(f"작업 완료 - Job ID: {job_id}")
                    # 백그라운드에서 결과 후처리
                    if ml_result.result:
                        background_tasks.add_task(
                            process_completed_results, job_id, ml_result.result
                        )
                else:
                    logger.error(
                        f"작업 실패 - Job ID: {job_id}, Error: {ml_result.error_message}"
                    )
            else:
                # 알 수 없는 상태
                logger.warning(
                    f"알 수 없는 상태 - Job ID: {job_id}, Status: {ml_result.status}"
                )
                success = True

            if not success:
                raise HTTPException(status_code=500, detail="작업 상태 업데이트 실패")

        except Exception as e:
            logger.error(f"상태 업데이트 중 오류: {str(e)}")
            raise HTTPException(status_code=500, detail="상태 업데이트 실패")

        return MLResultResponse(status="received")

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"요청 데이터 검증 실패 - Validation Errors: {e.errors()}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Invalid request format",
                "validation_errors": e.errors(),
                "expected_format": {
                    "job_id": "string (required)",
                    "status": "string (required)",
                    "progress": "integer (optional)",
                    "message": "string (optional)",
                    "result": "object (optional)",
                    "error_message": "string (optional)",
                },
            },
        )
    except Exception as e:
        logger.error(f"ML 결과 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"결과 처리 실패: {str(e)}")


@router.get("/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """작업 상태 조회 (클라이언트 폴링용)"""

    # Job ID 검증
    if not job_id or job_id == "undefined" or job_id == "null":
        raise HTTPException(status_code=400, detail="올바른 Job ID가 필요합니다")

    # UUID 형식 검증
    try:
        import uuid

        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Job ID는 유효한 UUID 형식이어야 합니다")

    job_service = JobService(db)
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

    if job.status == "processing":
        return {
            "job_id": str(job.job_id),
            "status": job.status,
            "progress": job.progress,
        }
    else:
        # 완료된 경우 결과 데이터 포함
        response = {
            "job_id": str(job.job_id),
            "status": job.status,
            "progress": job.progress,
        }

        # 결과 데이터가 있으면 포함
        if job.result:
            response["result"] = job.result

        return response


@router.get("/ml-server/health")
async def check_ml_server_health():
    """
    ML 서버 상태 확인 엔드포인트
    - ML 서버 연결 상태 확인
    - 응답 시간 측정
    - 상세한 진단 정보 제공
    """
    try:
        import time

        ml_api_url = MODEL_SERVER_URL
        timeout = 10  # 헬스체크용 짧은 타임아웃

        logger.info(f"ML 서버 헬스체크 시작 - URL: {ml_api_url}")

        start_time = time.time()
        timeout_config = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            try:
                # 헬스체크 엔드포인트 시도
                async with session.get(f"{ml_api_url}/health") as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        result = await response.text()
                        return {
                            "status": "healthy",
                            "ml_server_url": ml_api_url,
                            "response_time_ms": round(response_time * 1000, 2),
                            "http_status": response.status,
                            "response": result[:200],  # 첫 200자만 표시
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "ml_server_url": ml_api_url,
                            "response_time_ms": round(response_time * 1000, 2),
                            "http_status": response.status,
                            "error": "Non-200 status code",
                        }
            except aiohttp.ClientConnectorError as e:
                response_time = time.time() - start_time
                return {
                    "status": "connection_failed",
                    "ml_server_url": ml_api_url,
                    "response_time_ms": round(response_time * 1000, 2),
                    "error": str(e),
                    "suggestion": "ML 서버가 실행 중인지 확인하세요",
                }
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                return {
                    "status": "timeout",
                    "ml_server_url": ml_api_url,
                    "response_time_ms": round(response_time * 1000, 2),
                    "timeout_seconds": timeout,
                    "error": "Health check timeout",
                }

    except Exception as e:
        return {
            "status": "error",
            "ml_server_url": MODEL_SERVER_URL,
            "error": str(e),
            "message": "헬스체크 중 예외 발생",
        }


# /jobs 엔드포인트 제거됨 - 보안상 위험하므로 삭제
# 모든 작업 목록 조회는 관리자 대시보드에서만 가능하도록 변경


# 백그라운드 태스크 함수들
async def trigger_ml_server(job_id: str, request: VideoProcessRequest, db_session=None):
    """EC2 ML 서버에 분석 요청을 전송하는 백그라운드 태스크"""

    try:
        logger.info(f"ML 서버에 요청 전송 - Job ID: {job_id}")

        # ML 서버로 전송할 페이로드 구성 (필수 파라미터만)
        payload = {
            "job_id": job_id,
            "video_url": request.video_url,
            "fastapi_base_url": FASTAPI_BASE_URL,  # 동적 콜백 URL 제공
            "language": request.language,  # 언어 설정 (frontend에서 지정 또는 auto)
        }

        # EC2 ML 서버에 비동기 요청 전송 (콜백 기반)
        await _send_request_to_ml_server(job_id, payload, db_session)

        logger.info(f"ML 서버에 요청 전송 완료 - Job ID: {job_id}")
        # 결과는 콜백(/result)으로 받음

    except Exception as e:
        logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")
        # 에러는 이미 _send_request_to_ml_server에서 처리됨


async def process_completed_results(job_id: str, results: Dict[str, Any]):
    """완료된 분석 결과를 후처리하는 백그라운드 태스크"""

    try:
        logger.info(f"결과 후처리 시작 - Job ID: {job_id}")

        # TODO: 실제 후처리 로직 구현
        # 1. 데이터베이스에 결과 저장
        # 2. S3에 결과 파일 저장
        # 3. 사용자에게 완료 알림 전송
        # 4. 웹훅 전송 (필요한 경우)

        logger.info(f"결과 후처리 완료 - Job ID: {job_id}")

    except Exception as e:
        logger.error(f"결과 후처리 중 오류 - Job ID: {job_id}, Error: {str(e)}")


async def handle_processing_error(job_id: str, error_message: str):
    """처리 오류를 처리하는 백그라운드 태스크"""

    try:
        logger.error(f"오류 후처리 시작 - Job ID: {job_id}, Error: {error_message}")

        # TODO: 실제 오류 처리 로직 구현
        # 1. 오류 로그를 데이터베이스에 저장
        # 2. 관리자에게 오류 알림 전송
        # 3. 사용자에게 오류 알림 전송

        logger.info(f"오류 후처리 완료 - Job ID: {job_id}")

    except Exception as e:
        logger.error(f"오류 후처리 중 예외 - Job ID: {job_id}, Exception: {str(e)}")


# ML 서버에 요청 전송 함수 (콜백 기반)
async def _send_request_to_ml_server(
    job_id: str,
    payload: Dict[str, Any],
    db_session=None,
    retry_count: int = 0,
    max_retries: int = 2,
) -> None:
    """EC2 ML 서버에 처리 요청만 전송 (결과는 콜백으로 받음)"""

    try:
        # ML_API.md 명세에 따른 ML 서버 URL

        ml_api_url = MODEL_SERVER_URL  # settings에서 가져온 ML 서버 URL 사용
        timeout = float(ML_API_TIMEOUT)  # settings에서 가져온 타임아웃 사용

        # ML_API.md 명세에 따른 요청 페이로드 (필수 파라미터만)
        api_payload = {
            "job_id": job_id,
            "video_url": payload.get("video_url"),
            "fastapi_base_url": payload.get("fastapi_base_url"),
            "language": payload.get("language", "auto"),  # Frontend 지정 언어 또는 자동 감지
        }

        if retry_count > 0:
            logger.info(
                f"ML 서버 요청 재시도 {retry_count}/{max_retries} - Job ID: {job_id}, URL: {ml_api_url}"
            )
        else:
            logger.info(f"ML 서버 요청 전송 시작 - Job ID: {job_id}, URL: {ml_api_url}")

        logger.info(f"요청 데이터: {api_payload}")
        logger.info(f"타임아웃 설정: {timeout}초")

        # ML 서버에 처리 요청만 전송
        timeout_config = aiohttp.ClientTimeout(total=timeout)

        request_start_time = asyncio.get_event_loop().time()

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(
                f"{ml_api_url}/api/upload-video/process-video",
                json=api_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ECS-FastAPI-Backend/1.0",
                },
            ) as response:
                request_duration = asyncio.get_event_loop().time() - request_start_time
                logger.info(f"ML 서버 응답 시간: {request_duration:.2f}초 - Job ID: {job_id}")

                if response.status == 200:
                    result = await response.json()

                    # 테스트/목 데이터 감지
                    if isinstance(result.get("result"), dict):
                        transcript = result["result"].get("transcript", "")
                        if "[테스트]" in transcript or "테스트 결과" in transcript:
                            logger.warning(
                                f"⚠️ ML 서버가 테스트 데이터를 반환했습니다 - Job ID: {job_id}"
                            )
                            logger.warning(f"반환된 테스트 데이터: {transcript}")
                            logger.warning(
                                f"실제 처리 시간: {request_duration:.2f}초 (예상: 20-30초)"
                            )

                    logger.info(f"ML 서버 요청 접수 성공 - Job ID: {job_id}")
                    logger.info(f"응답 상태: {result.get('status', 'unknown')}")
                    if "result" in result:
                        logger.info(
                            f"결과 포함 여부: True, 스크립트 길이: {len(str(result['result']))}"
                        )
                    else:
                        logger.info("결과 포함 여부: False")

                    # estimated_time 처리 (선택적)
                    if "estimated_time" in result:
                        logger.info(f"ML 서버 예상 처리 시간: {result['estimated_time']}초")
                else:
                    # 에러 응답 상세 처리
                    error_detail = {}
                    try:
                        error_detail = await response.json()
                    except Exception:
                        error_detail = {"message": await response.text()}

                    error_message = error_detail.get(
                        "message", f"ML Server returned {response.status}"
                    )
                    error_code = error_detail.get("error", {}).get(
                        "code", "ML_SERVER_ERROR"
                    )

                    # 데이터베이스 업데이트 (가능한 경우)
                    if db_session:
                        await _update_job_status_error(
                            db_session, job_id, error_message, error_code
                        )

                    raise Exception(f"ML 서버 요청 실패 {response.status}: {error_message}")

    except asyncio.TimeoutError:
        error_message = f"ML 서버 처리 타임아웃 ({timeout}초)"
        logger.error(f"🔴 ML 서버 요청 타임아웃 - Job ID: {job_id}")
        logger.error(f"ML 서버 URL: {ml_api_url}")
        logger.error(f"설정된 타임아웃: {timeout}초")

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(
                db_session, job_id, error_message, "TIMEOUT_ERROR"
            )

        raise Exception(error_message)

    except aiohttp.ClientConnectorError as e:
        error_message = f"ML 서버 연결 실패: {str(e)}"
        logger.error(f"🔴 ML 서버 연결 실패 - Job ID: {job_id}")
        logger.error(f"ML 서버 URL: {ml_api_url}")
        logger.error(f"연결 에러 상세: {str(e)}")
        logger.error("ML 서버가 실행 중인지 확인이 필요합니다")

        # 재시도 로직
        if retry_count < max_retries:
            wait_time = (retry_count + 1) * 5  # 5초, 10초, 15초 대기
            logger.info(f"🔄 {wait_time}초 후 재시도합니다... ({retry_count + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
            return await _send_request_to_ml_server(
                job_id, payload, db_session, retry_count + 1, max_retries
            )

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(
                db_session, job_id, error_message, "CONNECTION_ERROR"
            )

        raise Exception(error_message)

    except Exception as e:
        logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(db_session, job_id, str(e), "UNKNOWN_ERROR")

        raise


# 에러 상태 업데이트 헬퍼 함수
async def _update_job_status_error(
    db_session, job_id: str, error_message: str, error_code: str
):
    """Job 상태를 실패로 업데이트"""
    try:
        if db_session:
            job_service = JobService(db_session)
            job_service.update_job_status(
                job_id=job_id,
                status="failed",
                error_message=f"{error_code}: {error_message}",
            )
    except Exception as e:
        logger.error(f"Job 상태 업데이트 실패: {str(e)}")
