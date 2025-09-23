"""
ML API 라우터 - 프론트엔드 요구사항에 맞춘 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import uuid

from app.db.database import get_db
from app.services.job_service import JobService
from app.services.s3_service import s3_service
from app.schemas.ml_response import (
    JobStatusResponse,
    get_progress_message,
    create_error_response,
    create_success_response,
    simplify_ml_result,
)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])


# 프론트엔드 요구 스키마
class ProcessVideoRequest(BaseModel):
    """프론트엔드에서 보내는 비디오 처리 요청"""

    video_path: str
    enable_gpu: bool = True
    emotion_detection: bool = True
    # language: str = "auto"  # "ko", "en", "auto"
    max_workers: int = 4


class ProcessVideoResponse(BaseModel):
    """비디오 처리 시작 응답"""

    job_id: str
    message: str
    analysis_time_used: Optional[int] = None


# ML 서버와 통신할 때 사용하는 스키마
class VideoProcessRequest(BaseModel):
    """ML 서버로 보내는 비디오 처리 요청"""

    job_id: str
    video_url: str


@router.post("/process-video", response_model=ProcessVideoResponse)
async def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    프론트엔드에서 요청하는 비디오 처리 시작

    프론트엔드 요청 경로: POST /api/v1/ml/process-video
    """
    try:
        # Job ID 생성
        job_id = str(uuid.uuid4())

        logger.info(f"새 비디오 처리 요청 - Job ID: {job_id}, Video Path: {request.video_path}")

        # JobService를 사용해서 작업 생성
        job_service = JobService(db)

        # S3에서 video_path를 사용해서 presigned download URL 생성
        try:
            # S3 다운로드 URL 생성 (ML 서버가 접근할 수 있도록)
            video_download_url = s3_service.generate_download_url(request.video_path)
            logger.info(f"S3 다운로드 URL 생성 완료 - Job ID: {job_id}")
        except Exception as e:
            logger.error(f"S3 다운로드 URL 생성 실패 - Job ID: {job_id}, Error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"비디오 파일에 접근할 수 없습니다: {str(e)}")

        # 작업 생성 (processing 상태로 시작)
        success = job_service.create_job(
            job_id=job_id, status="processing", progress=0, file_key=request.video_path
        )

        if not success:
            raise HTTPException(status_code=500, detail="작업 생성에 실패했습니다.")

        # ML 서버로 전송할 요청 데이터 구성
        ml_request = VideoProcessRequest(job_id=job_id, video_url=video_download_url)

        # 백그라운드에서 ML 서버로 요청 전송
        background_tasks.add_task(trigger_ml_server_processing, job_id, ml_request, db)

        logger.info(f"비디오 처리 시작 - Job ID: {job_id}")

        # 프론트엔드가 기대하는 응답 형식
        return ProcessVideoResponse(
            job_id=job_id,
            message="Video processing started",
            analysis_time_used=estimate_processing_time(request.video_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비디오 처리 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"비디오 처리 요청 중 오류가 발생했습니다: {str(e)}")


@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    작업 상태 조회 - 프론트엔드 폴링용

    프론트엔드 기대 경로: GET /api/v1/ml/job-status/{jobId}
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)

        if not job:
            logger.warning(f"존재하지 않는 Job ID: {job_id}")
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "JOB_NOT_FOUND", f"작업 ID {job_id}를 찾을 수 없습니다."
                ).dict(),
            )

        # 진행률 정수로 변환 (프론트엔드 요구사항)
        progress = int(job.progress) if job.progress is not None else 0

        # 상태별 응답 구성
        response = JobStatusResponse(
            status=job.status,
            progress=progress,
            current_message=get_progress_message(progress),
            message=f"Processing video audio... ({progress}%)",
            error_message=job.error_message if hasattr(job, "error_message") else None,
        )

        # 완료된 경우 결과 데이터 포함
        if job.status == "completed" and job.result:
            try:
                simplified_result = simplify_ml_result(job.result, job_id)
                response.results = simplified_result
                logger.info(f"작업 완료 상태 조회 - Job ID: {job_id}")
            except Exception as e:
                logger.error(f"결과 간소화 실패 - Job ID: {job_id}, Error: {str(e)}")
                # 결과 처리 실패해도 상태는 반환
                response.error_message = "결과 처리 중 오류가 발생했습니다."

        elif job.status == "failed":
            response.error_message = (
                job.error_message
                if hasattr(job, "error_message")
                else "처리 중 오류가 발생했습니다."
            )
            logger.info(f"작업 실패 상태 조회 - Job ID: {job_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 상태 조회 실패 - Job ID: {job_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "STATUS_ERROR", "상태 조회 중 오류가 발생했습니다.", {"technical_info": str(e)}
            ).dict(),
        )


@router.post("/ml-results")
async def receive_ml_results(ml_result: Dict[str, Any], db: Session = Depends(get_db)):
    """
    ML 서버 콜백 엔드포인트

    ML 서버가 처리 완료 시 결과를 전송하는 엔드포인트
    """
    try:
        job_id = ml_result.get("job_id")
        if not job_id:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "INVALID_REQUEST", "job_id가 필요합니다."
                ).dict(),
            )

        logger.info(f"ML 결과 수신 - Job ID: {job_id}")

        job_service = JobService(db)

        # 작업 존재 확인
        job = job_service.get_job(job_id)
        if not job:
            logger.warning(f"존재하지 않는 Job ID: {job_id}")
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "JOB_NOT_FOUND", f"작업 ID {job_id}를 찾을 수 없습니다."
                ).dict(),
            )

        # 결과 처리
        result_data = ml_result.get("result", {})
        status = ml_result.get("status", "completed")

        if status == "failed":
            # 실패 상태 업데이트
            error_message = ml_result.get("error_message", "ML 처리 중 오류가 발생했습니다.")
            success = job_service.update_job_status(
                job_id=job_id, status="failed", progress=0, error_message=error_message
            )

            if not success:
                raise HTTPException(status_code=500, detail="작업 상태 업데이트 실패")

            logger.info(f"작업 실패로 상태 업데이트 - Job ID: {job_id}")

        else:
            # 성공 상태 업데이트
            success = job_service.update_job_status(
                job_id=job_id, status="completed", progress=100, result=result_data
            )

            if not success:
                raise HTTPException(status_code=500, detail="작업 상태 업데이트 실패")

            logger.info(f"작업 완료로 상태 업데이트 - Job ID: {job_id}")

        return create_success_response({"message": "결과가 성공적으로 처리되었습니다."})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ML 결과 처리 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "RESULTS_ERROR", "결과 처리 중 오류가 발생했습니다.", {"technical_info": str(e)}
            ).dict(),
        )


@router.get("/results/{job_id}")
async def get_results(job_id: str, db: Session = Depends(get_db)):
    """
    처리 완료된 결과 조회

    프론트엔드 요구사항: GET /api/results/{jobId}
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "JOB_NOT_FOUND", f"작업 ID {job_id}를 찾을 수 없습니다."
                ).dict(),
            )

        if job.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    "JOB_NOT_COMPLETED", f"작업이 아직 완료되지 않았습니다. 현재 상태: {job.status}"
                ).dict(),
            )

        if not job.result:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    "RESULTS_NOT_FOUND", "완료된 작업이지만 결과 데이터가 없습니다."
                ).dict(),
            )

        # 결과 간소화
        try:
            simplified_result = simplify_ml_result(job.result, job_id)
            logger.info(f"결과 조회 성공 - Job ID: {job_id}")
            return simplified_result

        except Exception as e:
            logger.error(f"결과 간소화 실패 - Job ID: {job_id}, Error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    "RESULTS_PROCESSING_ERROR",
                    "결과 처리 중 오류가 발생했습니다.",
                    {"technical_info": str(e)},
                ).dict(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 조회 실패 - Job ID: {job_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                "RESULTS_ERROR", "결과 조회 중 오류가 발생했습니다.", {"technical_info": str(e)}
            ).dict(),
        )


# 헬퍼 함수들
async def trigger_ml_server_processing(
    job_id: str, ml_request: VideoProcessRequest, db: Session
):
    """ML 서버로 비디오 처리 요청을 전송하는 백그라운드 태스크"""

    # 기존 ml_video.py의 ML 서버 통신 로직을 재사용
    from app.api.v1.ml_video import _send_request_to_ml_server

    try:
        logger.info(f"ML 서버에 처리 요청 전송 - Job ID: {job_id}")

        # ML 서버로 요청 전송
        await _send_request_to_ml_server(
            job_id, {"job_id": job_id, "video_url": ml_request.video_url}
        )

        logger.info(f"ML 서버 요청 전송 완료 - Job ID: {job_id}")

    except Exception as e:
        logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 작업 상태를 실패로 업데이트
        job_service = JobService(db)
        job_service.update_job_status(
            job_id=job_id,
            status="failed",
            progress=0,
            error_message=f"ML 서버 요청 실패: {str(e)}",
        )


def estimate_processing_time(video_path: str) -> int:
    """비디오 경로를 기반으로 예상 처리 시간 반환 (초)"""

    # 기본 추정 시간 (실제로는 비디오 길이나 크기에 따라 계산)
    # 임시로 고정값 반환
    return 180  # 3분
