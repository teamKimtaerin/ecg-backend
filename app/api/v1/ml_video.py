"""
ML 서버와의 통신을 위한 비디오 처리 API

EC2 ML 서버로부터 분석 결과를 받고, 비디오 처리 요청을 관리합니다.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import asyncio
import logging
import uuid
import os
import aiohttp

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
    result: Dict[str, Any]


class VideoProcessRequest(BaseModel):
    """비디오 처리 요청"""

    job_id: str
    video_url: str


class VideoProcessResponse(BaseModel):
    """비디오 처리 응답"""

    job_id: str
    status: str
    message: str
    status_url: str


class JobStatusResponse(BaseModel):
    """작업 상태 응답"""

    job_id: str
    status: str
    progress: float
    created_at: str
    last_updated: Optional[str] = None
    current_message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# 메모리 기반 작업 상태 저장소 (추후 Redis나 DB로 대체)
job_status_store: Dict[str, Dict[str, Any]] = {}

# 환경변수에서 ML 서버 설정 읽기
ML_SERVER_URL = os.getenv("ML_API_SERVER_URL", "http://localhost:8001")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


@router.post("/process-video", response_model=VideoProcessResponse)
async def process_video_request(
    request: VideoProcessRequest, background_tasks: BackgroundTasks
):
    """
    비디오 처리 요청을 받아 EC2 ML 서버로 전달
    """

    try:
        # 입력 검증
        if not request.video_url:
            raise HTTPException(
                status_code=400, detail="video_url은 필수입니다"
            )

        # 요청에서 받은 job_id 사용
        job_id = request.job_id

        # 초기 상태 설정
        job_status_store[job_id] = {
            "status": "processing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "video_url": request.video_url,
        }

        logger.info(f"새 비디오 처리 요청 - Job ID: {job_id}")

        # 백그라운드에서 EC2 ML 서버에 요청 전송
        background_tasks.add_task(trigger_ml_server, job_id, request)

        status_url = f"/api/upload-video/status/{job_id}"

        return VideoProcessResponse(
            job_id=job_id,
            status="processing",
            message="비디오 처리가 시작되었습니다",
            status_url=status_url,
        )

    except Exception as e:
        logger.error(f"비디오 처리 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"요청 처리 실패: {str(e)}")


@router.post("/result")
async def receive_ml_results(
    ml_result: MLResultRequest, background_tasks: BackgroundTasks
):
    """
    ML 서버로부터 분석 결과를 받는 엔드포인트

    ML 서버가 호출하는 엔드포인트:
    POST http://fastapi-backend:8000/api/upload-video/result
    """

    try:
        job_id = ml_result.job_id

        logger.info(f"ML 결과 수신 - Job ID: {job_id}")

        # 작업이 존재하는지 확인
        if job_id not in job_status_store:
            logger.warning(f"존재하지 않는 Job ID: {job_id}")
            raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

        # 작업 상태를 완료로 업데이트
        job_status_store[job_id].update(
            {
                "status": "completed",
                "progress": 100,
                "last_updated": datetime.now().isoformat(),
                "result": ml_result.result,
            }
        )

        logger.info(f"작업 완료 - Job ID: {job_id}")

        # 백그라운드에서 결과 후처리
        background_tasks.add_task(
            process_completed_results, job_id, ml_result.result
        )

        return {
            "status": "received"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ML 결과 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"결과 처리 실패: {str(e)}")


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """작업 상태 조회 (클라이언트 폴링용)"""

    if job_id not in job_status_store:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

    job_data = job_status_store[job_id]

    if job_data["status"] == "processing":
        return {
            "job_id": job_id,
            "status": "processing",
            "progress": job_data.get("progress", 0)
        }
    else:
        # 완료된 경우 결과 데이터 포함
        response = {
            "job_id": job_id,
            "status": "completed"
        }
        
        # 결과 데이터가 있으면 포함
        if "result" in job_data and job_data["result"]:
            response["result"] = job_data["result"]
            
        return response



@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_all_jobs():
    """모든 작업 목록 조회 (개발/테스트용)"""

    jobs = []
    for job_id, job_data in job_status_store.items():
        jobs.append(
            {
                "job_id": job_id,
                "status": job_data["status"],
                "progress": job_data.get("progress", 0.0),
                "created_at": job_data["created_at"],
                "last_updated": job_data.get("last_updated"),
            }
        )

    # 최신 순으로 정렬
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    return jobs


# 백그라운드 태스크 함수들
async def trigger_ml_server(job_id: str, request: VideoProcessRequest):
    """EC2 ML 서버에 분석 요청을 전송하는 백그라운드 태스크"""

    try:
        logger.info(f"ML 서버에 요청 전송 - Job ID: {job_id}")

        # ML 서버로 전송할 페이로드 구성
        payload = {
            "job_id": job_id,
            "video_url": request.video_url,
            "fastapi_base_url": FASTAPI_BASE_URL,
            "enable_gpu": True,  # 기본값
            "emotion_detection": True,  # 기본값
            "language": "auto",  # 기본값
            "max_workers": 4,  # 기본값
        }

        # 현재는 단순히 ML 서버에 Python 스크립트 실행 명령을 보낸다고 가정
        # 실제로는 다음 중 하나의 방식을 사용:
        # 1. HTTP API 호출 (ML 서버가 FastAPI 앱인 경우)
        # 2. SSH 명령 실행 (ML 서버가 스크립트인 경우)
        # 3. 메시지 큐 (SQS, RabbitMQ 등)

        # EC2 ML API 서버에 HTTP 요청 전송
        result = await _call_ml_api_server(job_id, payload)

        logger.info(
            f"ML API 호출 완료 - Job ID: {job_id}, 처리 시간: {result.get('processing_time', 0):.2f}초"
        )

        # 작업 상태를 완료로 업데이트 (결과 포함)
        job_status_store[job_id].update(
            {
                "status": "completed",
                "progress": 1.0,
                "completed_at": datetime.now().isoformat(),
                "results": result,
            }
        )

    except Exception as e:
        logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")

        # 작업 상태를 실패로 업데이트
        job_status_store[job_id].update(
            {"status": "failed", "error_message": f"ML 서버 요청 실패: {str(e)}"}
        )


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


# ML API 서버 호출 함수
async def _call_ml_api_server(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """EC2 ML API 서버에 HTTP 요청을 보내서 분석 결과 받기"""

    try:
        # EC2 ML API 서버 URL
        ml_api_url = os.getenv("ML_API_SERVER_URL", "http://localhost:8001")
        timeout = float(os.getenv("ML_API_TIMEOUT", "300"))  # 5분 타임아웃

        # API 요청 페이로드 구성
        api_payload = {
            "video_path": payload.get("video_path"),
            "video_url": payload.get("video_url"),
            "enable_gpu": payload.get("enable_gpu", True),
            "emotion_detection": payload.get("emotion_detection", True),
            "language": payload.get("language", "auto"),
            "max_workers": payload.get("max_workers", 4),
            "output_path": None,  # 필요시 추가
        }

        logger.info(f"ML API 호출 시작 - Job ID: {job_id}, URL: {ml_api_url}")
        logger.debug(f"API 요청 데이터: {api_payload}")

        # HTTP API 호출
        timeout_config = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(
                f"{ml_api_url}/transcribe",
                json=api_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ECS-FastAPI-Backend/1.0",
                },
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("success", False):
                        logger.info(f"ML API 호출 성공 - Job ID: {job_id}")
                        return result
                    else:
                        raise Exception(f"ML 분석 실패: {result}")

                else:
                    error_text = await response.text()
                    raise Exception(f"ML API 응답 오류 {response.status}: {error_text}")

    except asyncio.TimeoutError:
        logger.error(f"ML API 호출 타임아웃 - Job ID: {job_id}")
        raise Exception(f"ML API 호출 타임아웃 ({timeout}초)")

    except aiohttp.ClientConnectorError as e:
        logger.error(f"ML API 서버 연결 실패 - Job ID: {job_id}, Error: {str(e)}")
        raise Exception(f"ML API 서버 연결 실패: {str(e)}")

    except Exception as e:
        logger.error(f"ML API 호출 실패 - Job ID: {job_id}, Error: {str(e)}")
        raise
