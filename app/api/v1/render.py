"""
GPU 서버 렌더링 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging
import aiohttp
from app.db.database import get_db
from app.services.render_service import RenderService
from app.core.config import settings

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/render", tags=["render"])


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
    pollUrl: str
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
GPU_RENDER_SERVER_URL = getattr(settings, 'GPU_RENDER_SERVER_URL', 'http://gpu-server:8090')
GPU_RENDER_TIMEOUT = getattr(settings, 'GPU_RENDER_TIMEOUT', 1800)  # 30분
RENDER_CALLBACK_URL = getattr(settings, 'RENDER_CALLBACK_URL', settings.FASTAPI_BASE_URL)


@router.post("/create", response_model=CreateRenderResponse)
async def create_render_job(
    request: CreateRenderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    GPU 서버에서 비디오 렌더링 작업을 생성합니다.
    """
    try:
        # 입력 검증
        if not request.videoUrl:
            raise HTTPException(status_code=400, detail="videoUrl is required")

        if not request.scenario:
            raise HTTPException(status_code=400, detail="scenario is required")

        # 렌더링 서비스로 작업 생성
        render_service = RenderService(db)

        # 옵션 변환
        options_dict = request.options.dict() if request.options else {}

        render_job = render_service.create_render_job(
            video_url=request.videoUrl,
            scenario=request.scenario,
            options=options_dict,
            user_id=None,  # TODO: 인증 구현 후 user_id 추가
            video_name=None,  # TODO: 비디오 이름 추출
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
        background_tasks.add_task(trigger_gpu_server, str(render_job.job_id), gpu_request, db)

        return CreateRenderResponse(
            jobId=str(render_job.job_id),
            estimatedTime=render_job.estimated_time,
            pollUrl=f"/api/render/{render_job.job_id}/status",
            createdAt=render_job.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"렌더링 작업 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create render job: {str(e)}")


@router.get("/{job_id}/status", response_model=RenderStatusResponse)
async def get_render_status(job_id: str, db: Session = Depends(get_db)):
    """
    렌더링 작업의 현재 상태를 확인합니다.
    """
    render_service = RenderService(db)
    job = render_service.get_render_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
    db: Session = Depends(get_db)
):
    """
    진행 중인 렌더링 작업을 취소합니다.
    """
    render_service = RenderService(db)

    # 작업 존재 확인
    job = render_service.get_render_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 작업 취소
    success = render_service.cancel_render_job(job_id)

    if success:
        # GPU 서버에도 취소 요청 전송 (백그라운드)
        background_tasks.add_task(cancel_gpu_job, job_id)

        return CancelRenderResponse(
            success=True,
            message="Job cancelled successfully"
        )
    else:
        return CancelRenderResponse(
            success=False,
            message="Failed to cancel job or job is already completed"
        )


@router.get("/history", response_model=List[RenderHistoryItem])
async def get_render_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    렌더링 작업 이력을 조회합니다.
    """
    render_service = RenderService(db)

    # TODO: 인증 구현 후 user_id로 필터링
    history = render_service.get_render_job_history(user_id=None, limit=limit)

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
    callback: GPURenderCallback,
    db: Session = Depends(get_db)
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
            raise HTTPException(status_code=404, detail="Job not found")

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
            raise HTTPException(status_code=500, detail="Failed to update job status")

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GPU 콜백 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")


# 백그라운드 태스크 함수들
async def trigger_gpu_server(job_id: str, request: GPURenderRequest, db_session=None):
    """GPU 서버에 렌더링 요청을 전송하는 백그라운드 태스크"""
    try:
        logger.info(f"GPU 서버에 요청 전송 - Job ID: {job_id}")

        # GPU 서버로 요청 전송
        await _send_request_to_gpu_server(job_id, request.dict(), db_session)

        logger.info(f"GPU 서버에 요청 전송 완료 - Job ID: {job_id}")

    except Exception as e:
        logger.error(f"GPU 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")


async def _send_request_to_gpu_server(job_id: str, payload: Dict[str, Any], db_session=None) -> None:
    """GPU 서버에 렌더링 요청 전송"""
    try:
        gpu_api_url = GPU_RENDER_SERVER_URL
        timeout = float(GPU_RENDER_TIMEOUT)

        logger.info(f"GPU 서버 요청 전송 시작 - Job ID: {job_id}, URL: {gpu_api_url}")
        logger.debug(f"요청 데이터: {payload}")

        timeout_config = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(
                f"{gpu_api_url}/api/render/process",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ECG-Backend/1.0",
                },
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"GPU 서버 요청 접수 성공 - Job ID: {job_id}, Response: {result}")
                else:
                    error_text = await response.text()
                    error_message = f"GPU Server returned {response.status}: {error_text}"

                    # 데이터베이스 업데이트
                    if db_session:
                        await _update_job_error(db_session, job_id, error_message, "GPU_SERVER_ERROR")

                    raise Exception(error_message)

    except aiohttp.ClientConnectorError as e:
        error_message = f"GPU 서버 연결 실패: {str(e)}"
        logger.error(f"GPU 서버 연결 실패 - Job ID: {job_id}, Error: {str(e)}")

        if db_session:
            await _update_job_error(db_session, job_id, error_message, "CONNECTION_ERROR")

        raise Exception(error_message)

    except Exception as e:
        logger.error(f"GPU 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        if db_session:
            await _update_job_error(db_session, job_id, str(e), "UNKNOWN_ERROR")

        raise


async def _update_job_error(db_session, job_id: str, error_message: str, error_code: str):
    """작업 에러 상태 업데이트"""
    try:
        if db_session:
            render_service = RenderService(db_session)
            render_service.update_render_job_status(
                job_id=job_id,
                status="failed",
                error_message=error_message,
                error_code=error_code,
            )
    except Exception as e:
        logger.error(f"작업 상태 업데이트 실패: {str(e)}")


async def cancel_gpu_job(job_id: str):
    """GPU 서버에 작업 취소 요청"""
    try:
        gpu_api_url = GPU_RENDER_SERVER_URL

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{gpu_api_url}/api/render/{job_id}/cancel",
                headers={"User-Agent": "ECG-Backend/1.0"},
            ) as response:
                if response.status == 200:
                    logger.info(f"GPU 서버 작업 취소 성공 - Job ID: {job_id}")
                else:
                    logger.warning(f"GPU 서버 작업 취소 실패 - Job ID: {job_id}, Status: {response.status}")

    except Exception as e:
        logger.error(f"GPU 서버 작업 취소 요청 실패 - Job ID: {job_id}, Error: {str(e)}")