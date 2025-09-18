"""
YouTube Data API 엔드포인트
"""

import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.youtube_service import YouTubeService
from app.api.v1.auth import get_current_user
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
security = HTTPBearer()
youtube_service = YouTubeService()


# Pydantic 모델들
class VideoMetadata(BaseModel):
    """비디오 메타데이터"""
    title: str = Field(..., max_length=100, description="비디오 제목")
    description: str = Field(default="", max_length=5000, description="비디오 설명")
    tags: List[str] = Field(default=[], max_items=500, description="비디오 태그")
    privacy: str = Field(default="private", description="공개 설정 (private, unlisted, public)")
    categoryId: str = Field(default="22", description="카테고리 ID (기본: People & Blogs)")


class UploadRequest(BaseModel):
    """업로드 요청"""
    videoUrl: Optional[str] = None  # GPU 렌더링된 비디오 URL
    metadata: VideoMetadata


class UploadResponse(BaseModel):
    """업로드 응답"""
    upload_id: str
    status: str
    message: str


class UploadStatus(BaseModel):
    """업로드 상태"""
    upload_id: str
    status: str  # uploading, completed, failed
    progress: int
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    studio_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class QuotaStatus(BaseModel):
    """할당량 상태"""
    used: int
    limit: int
    remaining: int
    can_upload: bool
    uploads_available: int


class AuthUrlResponse(BaseModel):
    """인증 URL 응답"""
    auth_url: str
    message: str


# 업로드 상태 추적용 (실제로는 Redis 사용)
upload_status_store: Dict[str, Dict[str, Any]] = {}


@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_youtube_auth_url(
    current_user: UserResponse = Depends(get_current_user)
):
    """YouTube 업로드 권한을 위한 OAuth URL 생성"""
    try:
        auth_url = youtube_service.get_auth_url(current_user.id)

        return AuthUrlResponse(
            auth_url=auth_url,
            message="YouTube 인증을 위해 링크를 클릭하세요."
        )

    except Exception as e:
        logger.error(f"YouTube 인증 URL 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"인증 URL 생성에 실패했습니다: {str(e)}"
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    request: UploadRequest = None,
    file: UploadFile = File(None),
    metadata_json: str = Form(None),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """YouTube 비디오 업로드"""
    try:
        # 메타데이터 파싱
        if request:
            metadata = request.metadata
            video_url = request.videoUrl
        elif metadata_json:
            import json
            metadata_dict = json.loads(metadata_json)
            metadata = VideoMetadata(**metadata_dict)
            video_url = None
        else:
            raise HTTPException(
                status_code=400,
                detail="메타데이터가 필요합니다."
            )

        # 1. 할당량 확인
        quota_check = youtube_service.can_upload(db)
        if not quota_check['allowed']:
            raise HTTPException(
                status_code=429,
                detail=quota_check['reason']
            )

        # 2. 메타데이터 검증
        validation = youtube_service.validate_video_metadata(metadata.model_dump())
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"메타데이터 오류: {', '.join(validation['errors'])}"
            )

        # 3. 파일 처리
        if not file and not video_url:
            raise HTTPException(
                status_code=400,
                detail="업로드할 비디오 파일 또는 URL이 필요합니다."
            )

        # 파일 형식 검증
        if file:
            if not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                raise HTTPException(
                    status_code=400,
                    detail="지원하지 않는 파일 형식입니다. (mp4, mov, avi, mkv만 지원)"
                )

        # 4. 업로드 ID 생성
        upload_id = str(uuid.uuid4())

        # 5. 상태 초기화
        upload_status_store[upload_id] = {
            'status': 'preparing',
            'progress': 0,
            'video_id': None,
            'error': None,
            'created_at': datetime.now().isoformat(),
            'completed_at': None
        }

        # 6. 백그라운드에서 업로드 시작
        background_tasks.add_task(
            upload_video_background,
            upload_id,
            file,
            video_url,
            metadata.model_dump(),
            current_user.id,
            db  # DB 세션 전달
        )

        return UploadResponse(
            upload_id=upload_id,
            status="preparing",
            message="업로드 준비 중입니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube 업로드 요청 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"업로드 요청 처리에 실패했습니다: {str(e)}"
        )


@router.get("/status/{upload_id}", response_model=UploadStatus)
async def get_upload_status(upload_id: str):
    """업로드 진행률 조회"""
    if upload_id not in upload_status_store:
        raise HTTPException(
            status_code=404,
            detail="업로드를 찾을 수 없습니다."
        )

    status_data = upload_status_store[upload_id]

    response = UploadStatus(
        upload_id=upload_id,
        status=status_data['status'],
        progress=status_data['progress'],
        created_at=status_data.get('created_at'),
        completed_at=status_data.get('completed_at'),
        error=status_data.get('error')
    )

    # 완료 시 YouTube 링크 추가
    if status_data.get('video_id'):
        response.video_id = status_data['video_id']
        response.video_url = f"https://www.youtube.com/watch?v={status_data['video_id']}"
        response.studio_url = f"https://studio.youtube.com/video/{status_data['video_id']}/edit"

    return response


@router.get("/quota", response_model=QuotaStatus)
async def get_quota_status(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """할당량 상태 조회"""
    try:
        quota = youtube_service.get_quota_usage(db)
        uploads_available = quota['remaining'] // 1600  # 업로드당 1600 할당량

        return QuotaStatus(
            used=quota['used'],
            limit=quota['limit'],
            remaining=quota['remaining'],
            can_upload=quota['remaining'] >= 1600,
            uploads_available=uploads_available
        )

    except Exception as e:
        logger.error(f"할당량 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"할당량 조회에 실패했습니다: {str(e)}"
        )


@router.delete("/cancel/{upload_id}")
async def cancel_upload(upload_id: str):
    """업로드 취소"""
    if upload_id not in upload_status_store:
        raise HTTPException(
            status_code=404,
            detail="업로드를 찾을 수 없습니다."
        )

    status_data = upload_status_store[upload_id]

    if status_data['status'] in ['completed', 'failed']:
        raise HTTPException(
            status_code=400,
            detail="이미 완료되었거나 실패한 업로드는 취소할 수 없습니다."
        )

    # 상태를 취소로 변경
    upload_status_store[upload_id]['status'] = 'cancelled'
    upload_status_store[upload_id]['error'] = '사용자에 의해 취소됨'

    return {"message": "업로드가 취소되었습니다."}


async def upload_video_background(
    upload_id: str,
    file: UploadFile,
    video_url: Optional[str],
    metadata: Dict[str, Any],
    user_id: str,
    db: Session
):
    """백그라운드 업로드 작업"""
    temp_file_path = None

    try:
        # 상태 업데이트: 업로드 시작
        upload_status_store[upload_id]['status'] = 'uploading'
        upload_status_store[upload_id]['progress'] = 5

        # 1. 파일 준비
        if file:
            # 업로드된 파일 처리
            file_content = await file.read()
            temp_file_path = youtube_service.save_file_temporarily(
                file_content, file.filename
            )
        elif video_url:
            # URL에서 파일 다운로드 (GPU 렌더링된 경우)
            import requests
            response = requests.get(video_url)
            response.raise_for_status()

            temp_file_path = youtube_service.save_file_temporarily(
                response.content, 'video.mp4'
            )
        else:
            raise Exception("파일 또는 URL이 필요합니다.")

        upload_status_store[upload_id]['progress'] = 10

        # 2. YouTube 인증 (실제로는 사용자별 저장된 credentials 사용)
        # 여기서는 간소화된 버전 - 실제로는 OAuth 토큰 관리 필요
        logger.info("YouTube 인증 확인 중...")
        upload_status_store[upload_id]['progress'] = 15

        # 3. YouTube API 서비스 생성
        # 실제 구현에서는 사용자의 저장된 credentials를 사용해야 함
        # 지금은 데모용으로 진행률만 업데이트
        upload_status_store[upload_id]['progress'] = 20

        # 4. YouTube 업로드 시뮬레이션 (friends.mp4 테스트)
        logger.info(f"YouTube 업로드 시작 (friends.mp4) - Upload ID: {upload_id}")

        # 진행률 시뮬레이션 (실제로는 youtube_service.upload_video 호출)
        for progress in range(25, 95, 5):
            if upload_status_store[upload_id]['status'] == 'cancelled':
                return

            upload_status_store[upload_id]['progress'] = progress
            await asyncio.sleep(0.5)  # 업로드 시뮬레이션

        # 5. 업로드 완료 (실제로는 YouTube API 응답 처리)
        # mock_video_id = f"mock_video_{upload_id[:8]}"
        # upload_status_store[upload_id].update({
        #     'status': 'completed',
        #     'progress': 100,
        #     'video_id': mock_video_id,
        #     'completed_at': datetime.now().isoformat()
        # })

        # 실제 YouTube 업로드 코드 (OAuth 인증이 구현되면 주석 해제)
        """
        # YouTube 서비스 생성 (사용자 credentials 필요)
        service = youtube_service.build_authenticated_service(user_credentials)

        # 실제 업로드
        result = youtube_service.upload_video(
            service, temp_file_path, metadata, upload_id
        )

        upload_status_store[upload_id].update({
            'status': 'completed',
            'progress': 100,
            'video_id': result['id'],
            'completed_at': datetime.now().isoformat()
        })
        """

        # 현재는 테스트용 완료 처리 (friends.mp4 테스트)
        upload_status_store[upload_id].update({
            'status': 'completed',
            'progress': 100,
            'video_id': f"test_video_{upload_id[:8]}",
            'completed_at': datetime.now().isoformat()
        })

        # 할당량 업데이트 (실제 업로드 시에만)
        youtube_service.update_quota_usage(db, 1600)  # Videos.insert는 1600 할당량 소모

        logger.info(f"YouTube 업로드 완료 (friends.mp4 테스트) - Upload ID: {upload_id}")

    except Exception as e:
        error_message = str(e)
        logger.error(f"YouTube 업로드 실패 ({upload_id}): {error_message}")

        upload_status_store[upload_id].update({
            'status': 'failed',
            'progress': 0,
            'error': error_message,
            'completed_at': datetime.now().isoformat()
        })

    finally:
        # 임시 파일 정리
        if temp_file_path:
            youtube_service.cleanup_temp_file(temp_file_path)


def generate_upload_id() -> str:
    """업로드 ID 생성"""
    return str(uuid.uuid4())