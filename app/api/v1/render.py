"""
GPU 서버 렌더링 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.database import get_db
from app.services.render_service import RenderService
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.schemas.user import UserResponse
from app.utils.validators import validate_render_request
from app.utils.render_utils import extract_video_name, calculate_estimated_time
from app.utils.error_responses import RenderError
from app.tasks.gpu_tasks import trigger_gpu_server, cancel_gpu_job

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/render", tags=["render"])

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)

# Rate limit 에러는 slowapi middleware에서 자동 처리됨


# Pydantic 모델들
class RenderOptions(BaseModel):
    """렌더링 옵션"""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    quality: int = 90
    format: str = "mp4"


class CreateRenderRequest(BaseModel):
    """렌더링 작업 생성 요청"""

    videoUrl: str
    scenario: Dict[str, Any]  # MotionText scenario
    options: Optional[RenderOptions] = None


class CreateRenderResponse(BaseModel):
    """렌더링 작업 생성 응답"""

    jobId: str
    estimatedTime: int
    createdAt: str


class RenderStatusResponse(BaseModel):
    """렌더링 작업 상태 응답"""

    jobId: str
    status: str
    progress: int
    estimatedTimeRemaining: Optional[int] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    downloadUrl: Optional[str] = None
    error: Optional[str] = None


class CancelRenderResponse(BaseModel):
    """렌더링 작업 취소 응답"""

    success: bool
    message: str


class RenderHistoryItem(BaseModel):
    """렌더링 이력 항목"""

    jobId: str
    videoName: str
    status: str
    createdAt: str
    completedAt: Optional[str] = None
    downloadUrl: Optional[str] = None
    fileSize: Optional[int] = None
    duration: Optional[float] = None


class GPURenderRequest(BaseModel):
    """GPU 서버로 보내는 렌더링 요청"""

    job_id: str
    video_url: str
    scenario: Dict[str, Any]
    options: Dict[str, Any]
    callback_url: str


class GPURenderCallback(BaseModel):
    """GPU 서버로부터 받는 콜백"""

    job_id: str
    status: str
    progress: Optional[int] = None
    estimated_time_remaining: Optional[int] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


# 환경변수에서 GPU 서버 설정 읽기
GPU_RENDER_SERVER_URL = getattr(
    settings, "GPU_RENDER_SERVER_URL", "http://gpu-server:8090"
)
GPU_RENDER_TIMEOUT = getattr(settings, "GPU_RENDER_TIMEOUT", 1800)  # 30분
RENDER_CALLBACK_URL = getattr(
    settings, "RENDER_CALLBACK_URL", settings.FASTAPI_BASE_URL
)


@router.post("/create", response_model=CreateRenderResponse)
@limiter.limit("20/minute")  # 분당 20회 제한
async def create_render_job(
    request_obj: Request,
    request: CreateRenderRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GPU 서버에서 비디오 렌더링 작업을 생성합니다.
    """
    try:
        # 옵션 변환
        options_dict = request.options.model_dump() if request.options else {}

        # 상세 입력 검증
        validation_result = validate_render_request(
            request.videoUrl, request.scenario, options_dict
        )

        if not validation_result["valid"]:
            raise RenderError.validation_error(
                validation_result["reason"], validation_result["details"]
            )

        # 렌더링 서비스로 작업 생성
        render_service = RenderService(db)

        # 사용자 할당량 체크
        quota_check = render_service.check_user_quota(current_user.id)
        if not quota_check["allowed"]:
            quota_type = quota_check.get("quota_type", "unknown")
            raise RenderError.quota_exceeded(quota_check["reason"], quota_type)

        # 비디오 이름 추출
        video_name = extract_video_name(request.videoUrl)

        # 예상 렌더링 시간 계산
        estimated_time = calculate_estimated_time(request.scenario)

        render_job = render_service.create_render_job(
            video_url=request.videoUrl,
            scenario=request.scenario,
            options=options_dict,
            user_id=current_user.id,
            video_name=video_name,
            estimated_time=estimated_time,
        )

        logger.info(f"렌더링 작업 생성 - Job ID: {render_job.job_id}")

        # GPU 서버로 보낼 요청 준비
        gpu_request = GPURenderRequest(
            job_id=str(render_job.job_id),
            video_url=request.videoUrl,
            scenario=request.scenario,
            options=options_dict,
            callback_url=f"{RENDER_CALLBACK_URL}/api/render/callback",
        )

        # 백그라운드에서 GPU 서버에 요청 전송
        background_tasks.add_task(
            trigger_gpu_server, str(render_job.job_id), gpu_request.model_dump(), db
        )

        return CreateRenderResponse(
            jobId=str(render_job.job_id),
            estimatedTime=render_job.estimated_time,
            createdAt=render_job.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"렌더링 작업 생성 실패: {str(e)}")
        raise RenderError.job_creation_failed(str(e))


@router.get("/{job_id}/status", response_model=RenderStatusResponse)
async def get_render_status(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    렌더링 작업의 현재 상태를 확인합니다.
    """
    render_service = RenderService(db)
    job = render_service.get_render_job(job_id)

    if not job:
        raise RenderError.job_not_found(job_id)

    return RenderStatusResponse(
        jobId=str(job.job_id),
        status=job.status,
        progress=job.progress,
        estimatedTimeRemaining=job.estimated_time_remaining,
        startedAt=job.started_at.isoformat() if job.started_at else None,
        completedAt=job.completed_at.isoformat() if job.completed_at else None,
        downloadUrl=job.download_url,
        error=job.error_message,
    )


@router.post("/{job_id}/cancel", response_model=CancelRenderResponse)
async def cancel_render_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    진행 중인 렌더링 작업을 취소합니다.
    """
    render_service = RenderService(db)

    # 작업 존재 확인
    job = render_service.get_render_job(job_id)
    if not job:
        raise RenderError.job_not_found(job_id)

    # 작업 취소
    success = render_service.cancel_render_job(job_id)

    if success:
        # GPU 서버에도 취소 요청 전송 (백그라운드)
        background_tasks.add_task(cancel_gpu_job, job_id)

        return CancelRenderResponse(success=True, message="Job cancelled successfully")
    else:
        return CancelRenderResponse(
            success=False, message="Failed to cancel job or job is already completed"
        )


@router.get("/history", response_model=List[RenderHistoryItem])
async def get_render_history(
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    렌더링 작업 이력을 조회합니다.
    """
    render_service = RenderService(db)

    # 현재 사용자의 이력만 조회
    history = render_service.get_render_job_history(
        user_id=current_user.id, limit=limit
    )

    return [
        RenderHistoryItem(
            jobId=item["jobId"],
            videoName=item["videoName"],
            status=item["status"],
            createdAt=item["createdAt"],
            completedAt=item["completedAt"],
            downloadUrl=item["downloadUrl"],
            fileSize=item["fileSize"],
            duration=item["duration"],
        )
        for item in history
    ]


@router.post("/callback")
async def receive_gpu_callback(
    callback: GPURenderCallback, db: Session = Depends(get_db)
):
    """
    GPU 서버로부터 렌더링 진행상황 콜백을 받습니다.
    """
    try:
        job_id = callback.job_id

        logger.info(
            f"GPU 콜백 수신 - Job ID: {job_id}, Status: {callback.status}, Progress: {callback.progress}"
        )

        render_service = RenderService(db)

        # 작업 존재 확인
        job = render_service.get_render_job(job_id)
        if not job:
            logger.warning(f"존재하지 않는 Job ID: {job_id}")
            raise RenderError.job_not_found(job_id)

        # 상태 업데이트
        success = render_service.update_render_job_status(
            job_id=job_id,
            status=callback.status,
            progress=callback.progress,
            download_url=callback.download_url,
            file_size=callback.file_size,
            duration=callback.duration,
            error_message=callback.error_message,
            error_code=callback.error_code,
            estimated_time_remaining=callback.estimated_time_remaining,
        )

        if not success:
            raise RenderError.job_update_failed(job_id, "update status")

        # 완료/실패 시 사용량 통계 업데이트
        if callback.status in ["completed", "failed"]:
            updated_job = render_service.get_render_job(job_id)
            if updated_job:
                render_service.update_usage_stats(updated_job)

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GPU 콜백 처리 중 오류: {str(e)}")
        raise RenderError.callback_processing_failed(str(e))
