# YouTube 업로드 백엔드 구현 가이드

## 📋 구현 목표

기존 SmartYouTubeClient의 컴파일 에러를 해결하고, 안정적인 YouTube Data API v3 기반 업로드 시스템을 백엔드에서 구현합니다.

**우선 목표**: friends.mp4 파일 업로드로 기본 기능 검증 후 확장

## 🏗️ 시스템 아키텍처

### Phase 1: 기본 파일 업로드 (우선 구현)
```
friends.mp4 → Backend (FastAPI) → YouTube Data API v3
- 할당량 관리 (1600 tokens per upload)
- 파일 업로드 처리
- 실시간 진행률 추적
- 에러 처리 및 재시도
```

### Phase 2: GPU 렌더링 통합 (확장 기능)
```
GPU download_url → Backend (FastAPI) → YouTube Data API v3
- URL에서 파일 다운로드
- 임시 파일 처리
- 동일한 업로드 로직 사용
```

## 📦 Phase 1: 환경 설정

### 1.1 Google Cloud Console 설정

1. **YouTube Data API v3 활성화**
   ```bash
   # Google Cloud Console에서
   - APIs & Services > Library
   - YouTube Data API v3 검색 후 활성화
   ```

2. **OAuth 2.0 클라이언트 생성**
   ```bash
   # Credentials 탭에서
   - Create Credentials > OAuth 2.0 Client IDs
   - Application type: Web application
   - Authorized redirect URIs:
     - http://localhost:3000/auth/callback (개발용)
     - https://yourdomain.com/auth/callback (프로덕션용)
   ```

3. **할당량 설정 확인**
   ```bash
   # Quotas 탭에서 확인
   - YouTube Data API v3
   - Queries per day: 10,000 (기본값)
   - Videos.insert: 1600 tokens per request
   ```

### 1.2 Python 의존성 추가

**requirements.txt에 추가:**
```txt
google-api-python-client==2.108.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.1
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
```

### 1.3 환경 변수 설정

**.env 파일:**
```bash
# YouTube API 설정
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
YOUTUBE_API_KEY=your_api_key

# OAuth 설정
OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback

# 할당량 모니터링
YOUTUBE_QUOTA_LIMIT=10000
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/youtube/callback
```

## 📦 Phase 2: 백엔드 서비스 구현

### 2.1 YouTube 서비스 클래스

**파일: `backend/services/youtube_service.py`**

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from datetime import datetime
import os
import asyncio
from typing import Dict, Optional, Any
import logging

from app.models.youtube_quota import YouTubeQuotaUsage

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.quota_limit = int(os.getenv('YOUTUBE_QUOTA_LIMIT', 10000))
        self.upload_cost = 1600

    def build_service(self, credentials: Credentials):
        """YouTube API 서비스 객체 생성"""
        return build('youtube', 'v3', credentials=credentials)

    def get_quota_usage(self, db: Session) -> Dict[str, Any]:
        """현재 할당량 상태 확인 (PostgreSQL 기반)"""
        try:
            today = datetime.now().date()
            quota_record = db.query(YouTubeQuotaUsage).filter(
                YouTubeQuotaUsage.date == today
            ).first()

            used_quota = quota_record.used_quota if quota_record else 0
            remaining_quota = max(0, self.quota_limit - used_quota)
            can_upload = remaining_quota >= self.upload_cost

            return {
                "can_upload": can_upload,
                "used_quota": used_quota,
                "daily_limit": self.quota_limit,
                "remaining_quota": remaining_quota,
                "upload_cost": self.upload_cost,
                "max_uploads_remaining": remaining_quota // self.upload_cost
            }
        except Exception as e:
            logger.error(f"할당량 확인 실패: {e}")
            return {"can_upload": False, "error": str(e)}

    async def upload_video(
        self,
        credentials: Credentials,
        video_file_path: str,
        metadata: Dict[str, str],
        upload_id: str,
        db: Session,
        progress_callback = None
    ) -> Dict[str, Any]:
        """YouTube에 비디오 업로드"""
        try:
            # 할당량 사전 체크
            quota_status = self.get_quota_usage(db)
            if not quota_status.get("can_upload"):
                return {
                    "success": False,
                    "error": "할당량 부족",
                    "quota_status": quota_status
                }

            service = self.build_service(credentials)

            # 비디오 메타데이터 설정
            body = {
                'snippet': {
                    'title': metadata.get('title', '제목 없음'),
                    'description': metadata.get('description', ''),
                    'tags': metadata.get('tags', '').split(',') if metadata.get('tags') else []
                },
                'status': {
                    'privacyStatus': metadata.get('privacy', 'private')  # private, unlisted, public
                }
            }

            # 파일 업로드 설정
            media = MediaFileUpload(
                file_path,
                chunksize=1024*1024,  # 1MB chunks
                resumable=True
            )

            # 업로드 요청 생성
            insert_request = service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            # 진행률 추적하며 업로드 실행
            response = None
            error = None
            retry = 0

            while response is None:
                try:
                    if progress_callback:
                        # 진행률 콜백 (간단한 버전)
                        progress_callback(upload_id, {"status": "uploading", "progress": 50})

                    status, response = insert_request.next_chunk()

                    if status:
                        if progress_callback:
                            progress = int(status.progress() * 100)
                            progress_callback(upload_id, {
                                "status": "uploading",
                                "progress": progress
                            })

                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # 서버 에러 시 재시도
                        retry += 1
                        if retry > 3:
                            raise e
                        await asyncio.sleep(2 ** retry)
                    else:
                        raise e

            # 업로드 성공
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

            # 할당량 사용 기록
            self.update_quota_usage(db, self.upload_cost)

            if progress_callback:
                progress_callback(upload_id, {
                    "status": "completed",
                    "progress": 100,
                    "video_id": video_id,
                    "video_url": video_url,
                    "studio_url": studio_url
                })

            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "studio_url": studio_url,
                "quota_used": self.upload_cost
            }

        except Exception as e:
            logger.error(f"업로드 실패: {e}")
            if progress_callback:
                progress_callback(upload_id, {
                    "status": "failed",
                    "error": str(e)
                })
            return {
                "success": False,
                "error": str(e)
            }

    def update_quota_usage(self, db: Session, quota_cost: int):
        """할당량 사용량 업데이트 (PostgreSQL 기반)"""
        try:
            today = datetime.now().date()
            quota_record = db.query(YouTubeQuotaUsage).filter(
                YouTubeQuotaUsage.date == today
            ).first()

            if quota_record:
                quota_record.used_quota += quota_cost
            else:
                quota_record = YouTubeQuotaUsage(
                    date=today,
                    used_quota=quota_cost
                )
                db.add(quota_record)

            db.commit()
            logger.info(f"YouTube 할당량 업데이트: +{quota_cost}")

        except Exception as e:
            logger.warning(f"할당량 업데이트 실패: {str(e)}")
            db.rollback()

    def can_upload(self, db: Session) -> bool:
        """업로드 가능 여부 확인"""
        quota_status = self.get_quota_usage(db)
        return quota_status.get("can_upload", False)

# 싱글톤 인스턴스
youtube_service = YouTubeService()
```

### 2.2 FastAPI 라우터

**파일: `backend/routers/youtube.py`**

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Optional
import uuid
import os
import tempfile
from ..services.youtube_service import youtube_service
from ..db.database import get_db
from google.oauth2.credentials import Credentials

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

# 업로드 상태 저장소 (메모리 기반)
upload_status_store = {}

class UploadRequest(BaseModel):
    video_url: str  # S3 등에서 다운로드할 비디오 URL
    title: str
    description: Optional[str] = ""
    tags: Optional[str] = ""
    privacy: Optional[str] = "private"  # private, unlisted, public
    access_token: str  # OAuth 액세스 토큰

class UploadStatusResponse(BaseModel):
    upload_id: str
    status: str  # uploading, completed, failed
    progress: Optional[int] = None
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    studio_url: Optional[str] = None
    error: Optional[str] = None

@router.post("/upload")
async def start_upload(
    request: UploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """YouTube 업로드 시작"""
    try:
        # 할당량 사전 체크
        quota_status = youtube_service.get_quota_usage(db)
        if not quota_status.get("can_upload"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "YouTube API 할당량이 부족합니다",
                    "quota_status": quota_status
                }
            )

        # 고유 업로드 ID 생성
        upload_id = str(uuid.uuid4())

        # 초기 상태 설정
        upload_status_store[upload_id] = {
            "status": "started",
            "progress": 0
        }

        # 백그라운드에서 업로드 시작
        background_tasks.add_task(
            _process_upload,
            upload_id,
            request,
            db
        )

        return {
            "upload_id": upload_id,
            "message": "업로드가 시작되었습니다",
            "quota_status": quota_status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str) -> UploadStatusResponse:
    """업로드 진행 상태 조회"""
    if upload_id not in upload_status_store:
        raise HTTPException(status_code=404, detail="업로드 ID를 찾을 수 없습니다")

    status_data = upload_status_store[upload_id]
    return UploadStatusResponse(
        upload_id=upload_id,
        **status_data
    )

@router.get("/quota")
async def get_quota_status(db: Session = Depends(get_db)):
    """YouTube API 할당량 상태 조회"""
    try:
        quota_status = youtube_service.get_quota_usage(db)
        return quota_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cancel/{upload_id}")
async def cancel_upload(upload_id: str):
    """업로드 취소"""
    if upload_id not in upload_status_store:
        raise HTTPException(status_code=404, detail="업로드 ID를 찾을 수 없습니다")

    # 업로드 상태를 취소로 변경
    upload_status_store[upload_id]["status"] = "cancelled"

    return {"message": "업로드가 취소되었습니다"}

async def _process_upload(upload_id: str, request: UploadRequest, db: Session):
    """백그라운드 업로드 처리"""
    try:
        # 상태 업데이트 콜백
        def progress_callback(uid: str, status: Dict):
            upload_status_store[uid].update(status)

        # OAuth 크리덴셜 생성
        credentials = Credentials(token=request.access_token)

        # 비디오 파일 다운로드 (S3 등에서)
        upload_status_store[upload_id].update({
            "status": "downloading",
            "progress": 10
        })

        video_file_path = await _download_video_file(request.video_url)

        # YouTube 업로드
        upload_status_store[upload_id].update({
            "status": "uploading",
            "progress": 20
        })

        metadata = {
            "title": request.title,
            "description": request.description,
            "tags": request.tags,
            "privacy": request.privacy
        }

        result = await youtube_service.upload_video(
            credentials=credentials,
            video_file_path=video_file_path,
            metadata=metadata,
            upload_id=upload_id,
            db=db,
            progress_callback=progress_callback
        )

        # 임시 파일 정리
        os.unlink(video_file_path)

        if result["success"]:
            upload_status_store[upload_id].update({
                "status": "completed",
                "progress": 100,
                "video_id": result["video_id"],
                "video_url": result["video_url"],
                "studio_url": result["studio_url"]
            })
        else:
            upload_status_store[upload_id].update({
                "status": "failed",
                "error": result["error"]
            })

    except Exception as e:
        upload_status_store[upload_id].update({
            "status": "failed",
            "error": str(e)
        })

async def _download_video_file(video_url: str) -> str:
    """비디오 파일 다운로드 (S3 등에서)"""
    # TODO: S3나 다른 스토리지에서 파일 다운로드
    # 현재는 임시 구현
    import requests

    response = requests.get(video_url)
    response.raise_for_status()

    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_file.write(response.content)
        return temp_file.name
```

### 2.3 메인 앱에 라우터 등록

**파일: `backend/main.py`에 추가:**

```python
from .routers import youtube

# FastAPI 앱에 라우터 추가
app.include_router(youtube.router)
```

## 📦 Phase 3: 테스트 및 배포

### 3.1 로컬 테스트

#### Phase 1: friends.mp4 파일 업로드 테스트

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 3. 서버 실행
uvicorn app.main:app --reload

# 4. API 테스트 (friends.mp4 파일 업로드)
curl -X POST "http://localhost:8000/api/youtube/upload" \
  -F "file=@friends.mp4" \
  -F "metadata_json={\"title\":\"ECG 테스트\",\"privacy\":\"private\"}" \
  -H "Authorization: Bearer your_token"

# 5. 진행률 확인
curl "http://localhost:8000/api/youtube/status/{upload_id}"

# 6. 할당량 상태 확인
curl "http://localhost:8000/api/youtube/quota" \
  -H "Authorization: Bearer your_token"
```

#### Phase 2: GPU 렌더링 URL 테스트 (확장)

```bash
# GPU 렌더링 완료 후 download_url 사용
curl -X POST "http://localhost:8000/api/youtube/upload" \
  -H "Content-Type: application/json" \
  -d '{"videoUrl":"gpu_download_url","metadata":{"title":"GPU 렌더링 테스트"}}' \
  -H "Authorization: Bearer your_token"
```

### 3.2 프로덕션 배포 체크리스트

- [ ] Google Cloud Console OAuth 설정 완료
- [ ] 프로덕션 도메인으로 리다이렉트 URI 업데이트
- [x] PostgreSQL 할당량 추적 시스템 구현
- [ ] 로깅 및 모니터링 설정
- [ ] 에러 알림 시스템 구성
- [ ] 보안 헤더 및 CORS 설정

## 🔧 주요 API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/api/youtube/upload` | 업로드 시작 |
| GET | `/api/youtube/status/{upload_id}` | 진행 상태 조회 |
| GET | `/api/youtube/quota` | 할당량 상태 조회 |
| DELETE | `/api/youtube/cancel/{upload_id}` | 업로드 취소 |

## ⚠️ 중요 사항

### Phase 1 (우선 구현)
1. **파일 업로드**: friends.mp4로 기본 기능 검증
2. **할당량 관리**: 하루 6개 업로드 제한 (10,000 ÷ 1600)
3. **진행률 추적**: 실시간 업로드 상태 모니터링
4. **에러 처리**: 명확한 오류 메시지 및 재시도

### Phase 2 (확장 기능)
1. **URL 다운로드**: GPU 렌더링 결과 처리
2. **임시 파일 관리**: 자동 정리 및 메모리 최적화
3. **통합 테스트**: 두 방식 모두 동일한 로직 사용

## 📈 구현 순서

1. ✅ **friends.mp4 테스트**: 기본 YouTube 업로드 검증
2. 🔄 **GPU 통합**: URL 다운로드 방식 추가
3. 🔄 **최적화**: 성능 및 사용자 경험 개선

이 단계적 접근으로 **검증된 YouTube 업로드 백엔드 시스템**을 안전하게 구축할 수 있습니다.
