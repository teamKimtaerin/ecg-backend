"""
GPU 렌더링 백그라운드 태스크
"""

import aiohttp
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.render_service import RenderService

logger = logging.getLogger(__name__)

# GPU 서버 설정
GPU_RENDER_SERVER_URL = getattr(
    settings, "GPU_RENDER_SERVER_URL", "http://gpu-server:8090"
)
GPU_RENDER_TIMEOUT = getattr(settings, "GPU_RENDER_TIMEOUT", 1800)  # 30분
RENDER_CALLBACK_URL = getattr(
    settings, "RENDER_CALLBACK_URL", settings.FASTAPI_BASE_URL
)


async def trigger_gpu_server(
    job_id: str, request_data: Dict[str, Any], db_session: Session = None
):
    """GPU 서버에 렌더링 요청을 전송하는 백그라운드 태스크"""
    try:
        logger.info(f"GPU 서버에 요청 전송 - Job ID: {job_id}")

        # GPU 서버로 요청 전송
        await _send_request_to_gpu_server(job_id, request_data, db_session)

        logger.info(f"GPU 서버에 요청 전송 완료 - Job ID: {job_id}")

    except Exception as e:
        logger.error(f"GPU 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 실패 시 작업 상태 업데이트
        if db_session:
            render_service = RenderService(db_session)
            render_service.update_render_job_status(
                job_id=job_id,
                status="failed",
                error_message=str(e),
                error_code="GPU_SERVER_ERROR",
            )


async def _send_request_to_gpu_server(
    job_id: str, payload: Dict[str, Any], db_session: Session = None
) -> None:
    """GPU 서버에 렌더링 요청 전송"""
    try:
        # GPU 서버 요청 데이터 구성
        gpu_request = {
            "jobId": job_id,
            "videoUrl": payload.get("videoUrl"),
            "scenario": payload.get("scenario"),
            "options": payload.get("options", {}),
            "callbackUrl": f"{RENDER_CALLBACK_URL}/api/render/callback",
        }

        logger.info(f"GPU 서버 요청 데이터: {gpu_request}")

        # HTTP 요청 전송
        timeout = aiohttp.ClientTimeout(total=GPU_RENDER_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{GPU_RENDER_SERVER_URL}/render",
                json=gpu_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"GPU 서버 응답 성공 - Job ID: {job_id}, Result: {result}")

                    # 작업 상태를 processing으로 업데이트
                    if db_session:
                        render_service = RenderService(db_session)
                        render_service.update_render_job_status(
                            job_id=job_id, status="processing"
                        )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"GPU 서버 요청 실패 - Job ID: {job_id}, Status: {response.status}, Error: {error_text}"
                    )

                    # 실패 상태로 업데이트
                    if db_session:
                        render_service = RenderService(db_session)
                        render_service.update_render_job_status(
                            job_id=job_id,
                            status="failed",
                            error_message=f"GPU server error: {error_text}",
                            error_code=f"GPU_SERVER_{response.status}",
                        )

    except aiohttp.ClientError as e:
        logger.error(f"GPU 서버 연결 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 네트워크 오류 시 작업 상태 업데이트
        if db_session:
            render_service = RenderService(db_session)
            render_service.update_render_job_status(
                job_id=job_id,
                status="failed",
                error_message=f"Network error: {str(e)}",
                error_code="NETWORK_ERROR",
            )
        raise

    except Exception as e:
        logger.error(f"GPU 서버 요청 중 예상치 못한 오류 - Job ID: {job_id}, Error: {str(e)}")

        # 일반 오류 시 작업 상태 업데이트
        if db_session:
            render_service = RenderService(db_session)
            render_service.update_render_job_status(
                job_id=job_id,
                status="failed",
                error_message=str(e),
                error_code="UNEXPECTED_ERROR",
            )
        raise


def get_gpu_server_status() -> Dict[str, Any]:
    """GPU 서버 상태 확인 (동기 함수)"""
    return {
        "server_url": GPU_RENDER_SERVER_URL,
        "timeout": GPU_RENDER_TIMEOUT,
        "callback_url": RENDER_CALLBACK_URL,
    }


async def check_gpu_server_health() -> bool:
    """GPU 서버 헬스체크"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10초 타임아웃
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{GPU_RENDER_SERVER_URL}/health") as response:
                return response.status == 200
    except Exception as e:
        logger.warning(f"GPU 서버 헬스체크 실패: {str(e)}")
        return False


async def cancel_gpu_job(job_id: str):
    """GPU 서버에 작업 취소 요청"""
    try:
        timeout = aiohttp.ClientTimeout(total=30)  # 30초 타임아웃
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{GPU_RENDER_SERVER_URL}/api/render/{job_id}/cancel",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HOIT-Backend/1.0",
                },
            ) as response:
                if response.status == 200:
                    logger.info(f"GPU 서버 작업 취소 성공 - Job ID: {job_id}")
                else:
                    logger.warning(
                        f"GPU 서버 작업 취소 실패 - Job ID: {job_id}, Status: {response.status}"
                    )

    except Exception as e:
        logger.error(f"GPU 서버 작업 취소 요청 실패 - Job ID: {job_id}, Error: {str(e)}")
