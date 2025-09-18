"""
YouTube Data API v3 서비스
"""

import os
import json
import uuid
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, date
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.youtube_quota import YouTubeQuotaUsage

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube Data API v3 서비스"""

    def __init__(self):
        self.api_key = settings.youtube_api_key
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.youtube_redirect_uri
        self.quota_limit = settings.youtube_quota_limit

        # OAuth 스코프 설정
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube'
        ]

        # 메모리 기반 진행률 추적 (서버 재시작 시 초기화됨)
        self._upload_progress: Dict[str, int] = {}
        self._oauth_states: Dict[str, str] = {}

    def get_oauth_flow(self) -> Flow:
        """OAuth 2.0 플로우 생성"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        return flow

    def get_auth_url(self, user_id: str) -> str:
        """YouTube 업로드 권한을 위한 OAuth URL 생성"""
        flow = self.get_oauth_flow()

        # 상태값 생성 및 메모리에 저장 (10분 후 자동 정리는 별도 구현 필요)
        state = str(uuid.uuid4())
        self._oauth_states[state] = user_id

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )

        return authorization_url

    def build_authenticated_service(self, credentials):
        """인증된 YouTube API 서비스 생성"""
        try:
            return build('youtube', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"YouTube 서비스 생성 실패: {str(e)}")
            raise

    def upload_video(
        self,
        service,
        file_path: str,
        metadata: Dict[str, Any],
        upload_id: str
    ) -> Dict[str, Any]:
        """실제 YouTube 비디오 업로드"""
        try:
            # 메타데이터 구성
            body = {
                'snippet': {
                    'title': metadata.get('title', 'Untitled'),
                    'description': metadata.get('description', ''),
                    'tags': metadata.get('tags', [])
                },
                'status': {
                    'privacyStatus': metadata.get('privacy', 'private')
                }
            }

            # 파일 업로드 설정
            media = MediaFileUpload(
                file_path,
                chunksize=1024*1024,  # 1MB chunks
                resumable=True
            )

            # Videos.insert API 호출
            insert_request = service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            # 업로드 실행 및 진행률 추적
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self._update_upload_progress(upload_id, progress)
                    logger.info(f"업로드 진행률 ({upload_id}): {progress}%")

            # 할당량 사용량 업데이트는 별도로 호출해야 함 (DB 세션 필요)

            logger.info(f"YouTube 업로드 완료 - Video ID: {response['id']}")
            return response

        except HttpError as e:
            error_details = e.error_details[0] if e.error_details else {}
            error_reason = error_details.get('reason', 'unknown')
            error_message = error_details.get('message', str(e))

            logger.error(f"YouTube API 오류: {error_reason} - {error_message}")

            # 할당량 초과 오류 특별 처리
            if e.resp.status == 403 and 'quota' in error_message.lower():
                raise Exception("일일 할당량을 초과했습니다. 내일 다시 시도해주세요.")

            raise Exception(f"YouTube 업로드 실패: {error_message}")

        except Exception as e:
            logger.error(f"YouTube 업로드 중 오류 발생: {str(e)}")
            raise

    def _update_upload_progress(self, upload_id: str, progress: int):
        """업로드 진행률 업데이트 (메모리 기반)"""
        try:
            self._upload_progress[upload_id] = progress
        except Exception as e:
            logger.warning(f"진행률 업데이트 실패: {str(e)}")

    def get_upload_progress(self, upload_id: str) -> int:
        """업로드 진행률 조회 (메모리 기반)"""
        try:
            return self._upload_progress.get(upload_id, 0)
        except Exception as e:
            logger.warning(f"진행률 조회 실패: {str(e)}")
            return 0

    def get_quota_usage(self, db: Session) -> Dict[str, int]:
        """현재 할당량 사용량 조회 (PostgreSQL 기반)"""
        try:
            today = datetime.now().date()
            quota_record = db.query(YouTubeQuotaUsage).filter(
                YouTubeQuotaUsage.date == today
            ).first()

            used = quota_record.used_quota if quota_record else 0

            return {
                'used': used,
                'limit': self.quota_limit,
                'remaining': max(0, self.quota_limit - used)
            }
        except Exception as e:
            logger.warning(f"할당량 조회 실패: {str(e)}")
            return {
                'used': 0,
                'limit': self.quota_limit,
                'remaining': self.quota_limit
            }

    def update_quota_usage(self, db: Session, quota_cost: int):
        """할당량 사용량 업데이트 (PostgreSQL 기반)"""
        try:
            today = datetime.now().date()
            quota_record = db.query(YouTubeQuotaUsage).filter(
                YouTubeQuotaUsage.date == today
            ).first()

            if quota_record:
                current_usage = quota_record.used_quota
                quota_record.used_quota += quota_cost
                new_usage = quota_record.used_quota
            else:
                current_usage = 0
                new_usage = quota_cost
                quota_record = YouTubeQuotaUsage(
                    date=today,
                    used_quota=quota_cost
                )
                db.add(quota_record)

            db.commit()
            logger.info(f"YouTube 할당량 업데이트: {current_usage} -> {new_usage}")

        except Exception as e:
            logger.warning(f"할당량 업데이트 실패: {str(e)}")
            db.rollback()

    def can_upload(self, db: Session) -> Dict[str, Any]:
        """업로드 가능 여부 확인 (1600 quota 필요)"""
        quota = self.get_quota_usage(db)

        if quota['remaining'] < 1600:
            return {
                'allowed': False,
                'reason': f"할당량 부족 (남은 할당량: {quota['remaining']}/1600 필요)"
            }

        return {'allowed': True}

    def validate_video_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """비디오 메타데이터 검증"""
        errors = []

        # 제목 검증
        title = metadata.get('title', '').strip()
        if not title:
            errors.append("제목은 필수입니다.")
        elif len(title) > 100:
            errors.append("제목은 100자 이하여야 합니다.")

        # 설명 검증
        description = metadata.get('description', '')
        if len(description) > 5000:
            errors.append("설명은 5000자 이하여야 합니다.")

        # 태그 검증
        tags = metadata.get('tags', [])
        if len(tags) > 500:
            errors.append("태그는 최대 500개까지 가능합니다.")

        # 공개 설정 검증
        privacy = metadata.get('privacy', 'private')
        if privacy not in ['private', 'unlisted', 'public']:
            errors.append("올바르지 않은 공개 설정입니다.")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def save_file_temporarily(self, file_content: bytes, filename: str) -> str:
        """파일을 임시 저장하고 경로 반환"""
        try:
            # 안전한 파일명 생성
            safe_filename = f"{uuid.uuid4()}_{filename}"

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            logger.info(f"임시 파일 저장: {tmp_path}")
            return tmp_path

        except Exception as e:
            logger.error(f"임시 파일 저장 실패: {str(e)}")
            raise

    def cleanup_temp_file(self, file_path: str):
        """임시 파일 정리"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {str(e)}")
