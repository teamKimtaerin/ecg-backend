"""
통일된 에러 응답 포맷 유틸리티
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class RenderError:
    """렌더링 관련 에러 응답 생성기"""

    @staticmethod
    def validation_error(
        message: str, details: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """입력 검증 에러 (400)"""
        error_detail = {
            "error": "VALIDATION_ERROR",
            "message": message,
            "code": "RENDER_VALIDATION_FAILED",
        }
        if details:
            error_detail["details"] = details

        return HTTPException(status_code=400, detail=error_detail)

    @staticmethod
    def quota_exceeded(message: str, quota_type: str) -> HTTPException:
        """할당량 초과 에러 (403/429)"""
        status_code = 429 if quota_type == "concurrent" else 403
        error_detail = {
            "error": "QUOTA_EXCEEDED",
            "message": message,
            "code": f"RENDER_QUOTA_{quota_type.upper()}_EXCEEDED",
            "quota_type": quota_type,
        }

        return HTTPException(status_code=status_code, detail=error_detail)

    @staticmethod
    def job_not_found(job_id: str) -> HTTPException:
        """작업을 찾을 수 없음 (404)"""
        error_detail = {
            "error": "JOB_NOT_FOUND",
            "message": f"Render job with ID '{job_id}' not found",
            "code": "RENDER_JOB_NOT_FOUND",
            "job_id": job_id,
        }

        return HTTPException(status_code=404, detail=error_detail)

    @staticmethod
    def job_creation_failed(reason: str) -> HTTPException:
        """작업 생성 실패 (500)"""
        error_detail = {
            "error": "JOB_CREATION_FAILED",
            "message": f"Failed to create render job: {reason}",
            "code": "RENDER_JOB_CREATION_FAILED",
        }

        return HTTPException(status_code=500, detail=error_detail)

    @staticmethod
    def job_update_failed(job_id: str, operation: str) -> HTTPException:
        """작업 상태 업데이트 실패 (500)"""
        error_detail = {
            "error": "JOB_UPDATE_FAILED",
            "message": f"Failed to {operation} job '{job_id}'",
            "code": f"RENDER_JOB_{operation.upper()}_FAILED",
            "job_id": job_id,
        }

        return HTTPException(status_code=500, detail=error_detail)

    @staticmethod
    def callback_processing_failed(reason: str) -> HTTPException:
        """콜백 처리 실패 (500)"""
        error_detail = {
            "error": "CALLBACK_PROCESSING_FAILED",
            "message": f"GPU callback processing failed: {reason}",
            "code": "RENDER_CALLBACK_PROCESSING_FAILED",
        }

        return HTTPException(status_code=500, detail=error_detail)

    @staticmethod
    def rate_limit_exceeded(limit: str, retry_after: int = 60) -> HTTPException:
        """속도 제한 초과 (429)"""
        error_detail = {
            "error": "RATE_LIMIT_EXCEEDED",
            "message": f"Too many requests. Limit: {limit}",
            "code": "RENDER_RATE_LIMIT_EXCEEDED",
            "retry_after": retry_after,
        }

        return HTTPException(status_code=429, detail=error_detail)

    @staticmethod
    def status_query_failed(reason: str) -> HTTPException:
        """상태 조회 실패 (500)"""
        error_detail = {
            "error": "STATUS_QUERY_FAILED",
            "message": f"Failed to query render job status: {reason}",
            "code": "RENDER_STATUS_QUERY_FAILED",
        }

        return HTTPException(status_code=500, detail=error_detail)

    @staticmethod
    def internal_error(reason: str, context: Optional[str] = None) -> HTTPException:
        """내부 서버 에러 (500)"""
        error_detail = {
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"An internal error occurred: {reason}",
            "code": "RENDER_INTERNAL_ERROR",
        }
        if context:
            error_detail["context"] = context

        return HTTPException(status_code=500, detail=error_detail)
