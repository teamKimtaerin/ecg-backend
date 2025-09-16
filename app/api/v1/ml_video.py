"""
ML 서버와의 통신을 위한 비디오 처리 API

EC2 ML 서버로부터 분석 결과를 받고, 비디오 처리 요청을 관리합니다.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import logging
import aiohttp
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.job_service import JobService
from app.core.config import settings

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload-video", tags=["ml-video"])


# Pydantic 모델들
class ProcessingStatus(Enum):
    """처리 상태"""

    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MLResultRequest(BaseModel):
    """ML 서버로부터 받는 결과 요청"""

    job_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class ClientProcessRequest(BaseModel):
    """클라이언트로부터 받는 비디오 처리 요청"""

    fileKey: str


class VideoProcessRequest(BaseModel):
    """ML 서버로 보내는 비디오 처리 요청"""

    job_id: str
    video_url: str


class ClientProcessResponse(BaseModel):
    """클라이언트에게 보내는 비디오 처리 응답"""

    message: str
    jobId: str


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
async def request_process(
    request: ClientProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    클라이언트로부터 비디오 처리 요청을 받아 ML 서버로 전달
    """

    try:
        # 입력 검증
        if not request.fileKey:
            raise HTTPException(status_code=400, detail="fileKey는 필수입니다")

        # job_id 생성
        import uuid

        job_id = str(uuid.uuid4())

        # S3 URL 생성
        import os

        s3_bucket_name = os.getenv("S3_BUCKET_NAME", "default-bucket")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        video_url = (
            f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{request.fileKey}"
        )

        # PostgreSQL에 작업 생성
        job_service = JobService(db)
        job_service.create_job(
            job_id=job_id,
            status="processing",
            progress=0,
            video_url=video_url,
            file_key=request.fileKey,
        )

        logger.info(f"새 비디오 처리 요청 - Job ID: {job_id}")

        # VideoProcessRequest 객체 생성
        video_request = VideoProcessRequest(job_id=job_id, video_url=video_url)

        # 백그라운드에서 EC2 ML 서버에 요청 전송 (DB 세션 전달)
        background_tasks.add_task(trigger_ml_server, job_id, video_request, db)

        return ClientProcessResponse(message="Video processing started.", jobId=job_id)

    except Exception as e:
        logger.error(f"클라이언트 비디오 처리 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"요청 처리 실패: {str(e)}")


# /process-video 엔드포인트는 제거됨 (내부용으로 더 이상 필요하지 않음)
# 모든 비디오 처리는 /request-process를 통해 진행


@router.post("/result")
async def receive_ml_results(
    ml_result: MLResultRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    ML 서버로부터 분석 결과를 받는 엔드포인트

    ML 서버가 호출하는 엔드포인트:
    POST http://fastapi-backend:8000/api/upload-video/result
    """

    try:
        job_id = ml_result.job_id

        logger.info(
            f"ML 결과 수신 - Job ID: {job_id}, Status: {ml_result.status}, Progress: {ml_result.progress}"
        )

        # PostgreSQL에서 작업 상태 업데이트
        job_service = JobService(db)

        # 작업이 존재하는지 확인
        job = job_service.get_job(job_id)
        if not job:
            logger.warning(f"존재하지 않는 Job ID: {job_id}")
            raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

        # 상태에 따라 처리
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
            final_status = "completed" if ml_result.status == "completed" else "failed"
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
            logger.warning(f"알 수 없는 상태 - Job ID: {job_id}, Status: {ml_result.status}")
            success = True

        if not success:
            raise HTTPException(status_code=500, detail="작업 상태 업데이트 실패")

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ML 결과 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"결과 처리 실패: {str(e)}")


@router.get("/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """작업 상태 조회 (클라이언트 폴링용)"""

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


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_all_jobs(db: Session = Depends(get_db)):
    """모든 작업 목록 조회 (개발/테스트용)"""

    job_service = JobService(db)
    jobs_data = job_service.list_all_jobs()

    jobs = []
    for job in jobs_data:
        jobs.append(
            {
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at.isoformat(),
                "last_updated": job.updated_at.isoformat() if job.updated_at else None,
            }
        )

    return jobs


# 백그라운드 태스크 함수들
async def trigger_ml_server(job_id: str, request: VideoProcessRequest, db_session=None):
    """EC2 ML 서버에 분석 요청을 전송하는 백그라운드 태스크"""

    try:
        logger.info(f"ML 서버에 요청 전송 - Job ID: {job_id}")

        # ML 서버로 전송할 페이로드 구성 (Backend Server 통합 가이드에 따라 확장)
        payload = {
            "job_id": job_id,
            "video_url": request.video_url,
            "fastapi_base_url": FASTAPI_BASE_URL,  # 동적 콜백 URL 제공
            "enable_gpu": True,  # GPU 사용 여부
            "emotion_detection": True,  # 감정 분석 여부
            "language": "auto",  # 언어 설정 (기본값: auto)
            "max_workers": 4,  # 최대 워커 수
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
async def _send_request_to_ml_server(job_id: str, payload: Dict[str, Any], db_session=None) -> None:
    """EC2 ML 서버에 처리 요청만 전송 (결과는 콜백으로 받음)"""

    try:
        # ML_API.md 명세에 따른 ML 서버 URL

        ml_api_url = os.getenv("MODEL_SERVER_URL", "http://host.docker.internal:8080")
        timeout = float(os.getenv("ML_API_TIMEOUT", "30"))  # 요청만 전송하므로 짧은 타임아웃

        # ML_API.md 명세에 따른 요청 페이로드 (확장된 파라미터 포함)
        api_payload = {
            "job_id": job_id,
            "video_url": payload.get("video_url"),
            "fastapi_base_url": payload.get("fastapi_base_url"),
            "language": payload.get("language", "auto"),
            "enable_gpu": payload.get("enable_gpu", True),
            "emotion_detection": payload.get("emotion_detection", True),
            "max_workers": payload.get("max_workers", 4),
        }

        logger.info(f"ML 서버 요청 전송 시작 - Job ID: {job_id}, URL: {ml_api_url}")
        logger.debug(f"요청 데이터: {api_payload}")

        # ML 서버에 처리 요청만 전송
        timeout_config = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(
                f"{ml_api_url}/api/upload-video/process-video",
                json=api_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ECS-FastAPI-Backend/1.0",
                },
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"ML 서버 요청 접수 성공 - Job ID: {job_id}, Response: {result}"
                    )
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

                    error_message = error_detail.get("message", f"ML Server returned {response.status}")
                    error_code = error_detail.get("error", {}).get("code", "ML_SERVER_ERROR")

                    # 데이터베이스 업데이트 (가능한 경우)
                    if db_session:
                        await _update_job_status_error(db_session, job_id, error_message, error_code)

                    raise Exception(f"ML 서버 요청 실패 {response.status}: {error_message}")

    except asyncio.TimeoutError:
        error_message = f"ML 서버 처리 타임아웃 ({timeout}초)"
        logger.error(f"ML 서버 요청 타임아웃 - Job ID: {job_id}")

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(db_session, job_id, error_message, "TIMEOUT_ERROR")

        raise Exception(error_message)

    except aiohttp.ClientConnectorError as e:
        error_message = f"ML 서버 연결 실패: {str(e)}"
        logger.error(f"ML 서버 연결 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(db_session, job_id, error_message, "CONNECTION_ERROR")

        raise Exception(error_message)

    except Exception as e:
        logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 데이터베이스 업데이트 (가능한 경우)
        if db_session:
            await _update_job_status_error(db_session, job_id, str(e), "UNKNOWN_ERROR")

        raise


# 에러 상태 업데이트 헬퍼 함수
async def _update_job_status_error(db_session, job_id: str, error_message: str, error_code: str):
    """Job 상태를 실패로 업데이트"""
    try:
        if db_session:
            job_service = JobService(db_session)
            job_service.update_job_status(
                job_id=job_id,
                status="failed",
                error_message=f"{error_code}: {error_message}"
            )
    except Exception as e:
        logger.error(f"Job 상태 업데이트 실패: {str(e)}")
