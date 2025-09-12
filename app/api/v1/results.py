"""
Results API 라우터 - 프론트엔드가 기대하는 /api/results 경로 제공
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.services.job_service import JobService
from app.schemas.ml_response import (
    create_error_response,
    simplify_ml_result,
)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results/{job_id}")
async def get_results(job_id: str, db: Session = Depends(get_db)):
    """
    처리 완료된 결과 조회 - 프론트엔드 요구 경로

    프론트엔드 기대 경로: GET /api/results/{jobId}
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
