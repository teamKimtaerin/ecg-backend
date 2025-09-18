# 새로운 YouTube 업로드 기능 구현 가이드

## 📋 개요

기존 SmartYouTubeClient의 복잡성과 컴파일 에러 문제를 해결하기 위해 **간단하고 실용적인 새로운 YouTube 업로드 시스템**을 구현하는 가이드입니다.

### 🎯 단계별 목표 워크플로우

**Phase 1: 기본 파일 업로드 (우선 구현)**
```
friends.mp4 파일 선택 → [YouTube 업로드 버튼] → 업로드 모달 → YouTube Studio
```

**Phase 2: GPU 렌더링 통합 (확장 기능)**
```
편집 완료 → GPU 렌더링 → [YouTube 업로드 버튼] → 업로드 모달 → YouTube Studio
```

## 🚨 기존 시스템의 문제점

### SmartYouTubeClient.ts 이슈
1. **컴파일 에러**: `Buffer.from()` - Node.js 전용 API를 브라우저에서 사용
2. **API 구조 불일치**: 실제 YouTube Upload API와 맞지 않는 구현
3. **과도한 복잡성**: 캐시/할당량 최적화로 인한 복잡한 구조
4. **실사용 불가**: 현재 상태로는 실제 업로드 불가능

### 새로 구현하는 이유
- ✅ **컴파일 에러 없는 깨끗한 코드**
- ✅ **실제 YouTube API 스펙 준수**
- ✅ **간단하고 이해하기 쉬운 구조**
- ✅ **빠른 구현 및 테스트 가능**

## 🏗️ 새로운 시스템 아키텍처

### 핵심 설계 원칙
1. **단순성**: 복잡한 최적화보다 확실한 동작 우선
2. **실용성**: 실제 YouTube API 스펙 준수
3. **확장성**: 기본 기능 완성 후 점진적 최적화
4. **디버깅 용이성**: 명확한 에러 처리와 로깅

### 시스템 구성도

```
Frontend (React)           Backend (FastAPI)         YouTube API
┌─────────────────┐       ┌──────────────────┐      ┌─────────────┐
│ YouTubeUpload   │ POST  │ /api/youtube/    │ HTTP │ Videos.     │
│ Modal           │──────▶│ upload           │─────▶│ insert      │
│                 │       │ (friends.mp4)    │      │ (1600 quota)│
│ Progress Bar    │ GET   │ /api/youtube/    │      │             │
│                 │◀──────│ status/{id}      │      │             │
└─────────────────┘       └──────────────────┘      └─────────────┘
```

## 📅 2단계 구현 계획

### Phase 1: 기본 파일 업로드 구현 (1-2일) - 우선 구현

**목표**: friends.mp4 파일을 직접 업로드하여 YouTube 업로드 기능 검증

#### 1.1 환경 설정
```bash
# backend/.env
GOOGLE_CLIENT_ID=1076942061297-flpl289j4gi2a96ed8do37j16b9hcu97.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/youtube/callback
YOUTUBE_QUOTA_LIMIT=10000
JWT_SECRET=your_jwt_secret
```

#### 1.2 테스트 시나리오
```bash
# 1. friends.mp4 파일 준비 (프로젝트 루트에 이미 존재)
# 2. YouTube 업로드 API 테스트
# 3. 할당량 관리 검증
# 4. 진행률 추적 확인
```

#### 1.2 의존성 설치
```python
# backend/requirements.txt
google-auth==2.23.0
google-auth-oauthlib==1.1.0
google-api-python-client==2.100.0
fastapi==0.104.1
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
```

#### 1.3 YouTube API 서비스 구현

**backend/services/youtube_service.py**
```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session
from datetime import datetime
import os
import logging

from app.models.youtube_quota import YouTubeQuotaUsage

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.quota_limit = int(os.getenv('YOUTUBE_QUOTA_LIMIT', 10000))

    def build_authenticated_service(self, credentials):
        """인증된 YouTube API 서비스 생성"""
        return build('youtube', 'v3', credentials=credentials)

    def upload_video(self, service, file_path, metadata):
        """실제 YouTube 비디오 업로드"""

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

        # 업로드 실행
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"업로드 진행률: {progress}%")

        return response

    def get_quota_usage(self, db: Session):
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

    def can_upload(self, db: Session):
        """업로드 가능 여부 확인 (1600 quota 필요)"""
        quota = self.get_quota_usage(db)
        return quota['remaining'] >= 1600

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
```

#### 1.4 FastAPI 엔드포인트

**backend/routers/youtube.py**
```python
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
import tempfile
import os

from app.db.database import get_db
from app.models.youtube_quota import YouTubeQuotaUsage

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
security = HTTPBearer()
youtube_service = YouTubeService()

class VideoMetadata(BaseModel):
    title: str
    description: str = ""
    tags: list[str] = []
    privacy: str = "private"  # private, unlisted, public

class UploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str

# 업로드 상태 추적용 딕셔너리 (메모리 기반)
upload_status = {}

@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: VideoMetadata = None,
    token: str = Depends(security),
    db: Session = Depends(get_db)
):
    """YouTube 비디오 업로드"""

    # 1. 할당량 확인
    if not youtube_service.can_upload(db):
        raise HTTPException(
            status_code=429,
            detail="할당량 부족. 내일 다시 시도해주세요."
        )

    # 2. 파일 검증
    if not file.filename.endswith(('.mp4', '.mov', '.avi')):
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다."
        )

    # 3. 임시 파일 저장
    upload_id = generate_upload_id()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    # 4. 백그라운드에서 업로드 시작
    upload_status[upload_id] = {
        'status': 'uploading',
        'progress': 0,
        'video_id': None,
        'error': None
    }

    background_tasks.add_task(
        upload_video_background,
        upload_id,
        tmp_path,
        metadata.dict(),
        token.credentials,
        db
    )

    return UploadResponse(
        upload_id=upload_id,
        status="uploading",
        message="업로드가 시작되었습니다."
    )

@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """업로드 진행률 조회"""

    if upload_id not in upload_status:
        raise HTTPException(status_code=404, detail="업로드를 찾을 수 없습니다.")

    status = upload_status[upload_id]

    response = {
        'upload_id': upload_id,
        'status': status['status'],
        'progress': status['progress']
    }

    if status['video_id']:
        response['video_id'] = status['video_id']
        response['video_url'] = f"https://www.youtube.com/watch?v={status['video_id']}"
        response['studio_url'] = f"https://studio.youtube.com/video/{status['video_id']}/edit"

    if status['error']:
        response['error'] = status['error']

    return response

@router.get("/quota")
async def get_quota_status(
    token: str = Depends(security),
    db: Session = Depends(get_db)
):
    """할당량 상태 조회"""
    return youtube_service.get_quota_usage(db)

async def upload_video_background(upload_id: str, file_path: str, metadata: dict, credentials, db: Session):
    """백그라운드 업로드 작업"""
    try:
        # YouTube API 서비스 생성
        service = youtube_service.build_authenticated_service(credentials)

        # 업로드 시작
        upload_status[upload_id]['status'] = 'uploading'

        # 실제 업로드 (진행률 업데이트 포함)
        result = youtube_service.upload_video(service, file_path, metadata)

        # 업로드 완료
        upload_status[upload_id].update({
            'status': 'completed',
            'progress': 100,
            'video_id': result['id']
        })

        # 할당량 업데이트
        youtube_service.update_quota_usage(db, 1600)

    except Exception as e:
        upload_status[upload_id].update({
            'status': 'failed',
            'progress': 0,
            'error': str(e)
        })

    finally:
        # 임시 파일 삭제
        if os.path.exists(file_path):
            os.unlink(file_path)
```

### Phase 2: GPU 렌더링 통합 (1일) - 확장 기능

#### 2.1 YouTube 업로드 API 클라이언트

**src/lib/youtube/YouTubeUploader.ts**
```typescript
interface VideoMetadata {
  title: string
  description?: string
  tags?: string[]
  privacy: 'private' | 'unlisted' | 'public'
}

interface UploadResponse {
  upload_id: string
  status: string
  message: string
}

interface UploadStatus {
  upload_id: string
  status: 'uploading' | 'completed' | 'failed'
  progress: number
  video_id?: string
  video_url?: string
  studio_url?: string
  error?: string
}

interface QuotaStatus {
  used: number
  limit: number
  remaining: number
}

class YouTubeUploader {
  private baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

  /**
   * 비디오 업로드 시작
   */
  async uploadVideo(file: File, metadata: VideoMetadata): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))

    const token = this.getAuthToken()
    if (!token) {
      throw new Error('인증 토큰이 없습니다')
    }

    const response = await fetch(`${this.baseURL}/api/youtube/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '업로드 실패')
    }

    return response.json()
  }

  /**
   * 업로드 상태 조회
   */
  async getUploadStatus(uploadId: string): Promise<UploadStatus> {
    const response = await fetch(`${this.baseURL}/api/youtube/status/${uploadId}`)

    if (!response.ok) {
      throw new Error('상태 조회 실패')
    }

    return response.json()
  }

  /**
   * 할당량 상태 조회
   */
  async getQuotaStatus(): Promise<QuotaStatus> {
    const token = this.getAuthToken()
    if (!token) {
      throw new Error('인증 토큰이 없습니다')
    }

    const response = await fetch(`${this.baseURL}/api/youtube/quota`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error('할당량 조회 실패')
    }

    return response.json()
  }

  /**
   * 할당량 확인 (업로드 가능 여부)
   */
  async canUpload(): Promise<{ allowed: boolean; reason?: string }> {
    try {
      const quota = await this.getQuotaStatus()

      if (quota.remaining < 1600) {
        return {
          allowed: false,
          reason: `할당량 부족 (남은 할당량: ${quota.remaining}/1600 필요)`
        }
      }

      return { allowed: true }
    } catch (error) {
      return {
        allowed: false,
        reason: '할당량 확인 실패'
      }
    }
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token')
  }
}

export const youtubeUploader = new YouTubeUploader()
export type { VideoMetadata, UploadResponse, UploadStatus, QuotaStatus }
```

#### 2.2 YouTube 업로드 훅

**src/hooks/useYouTubeUpload.ts**
```typescript
import { useState, useEffect, useCallback } from 'react'
import { youtubeUploader, VideoMetadata, UploadStatus, QuotaStatus } from '@/lib/youtube/YouTubeUploader'

interface UseYouTubeUploadReturn {
  // 상태
  isUploading: boolean
  progress: number
  uploadStatus: UploadStatus | null
  quotaStatus: QuotaStatus | null
  error: string | null

  // 액션
  uploadVideo: (file: File, metadata: VideoMetadata) => Promise<void>
  cancelUpload: () => void
  checkQuota: () => Promise<void>
  clearError: () => void
}

export function useYouTubeUpload(): UseYouTubeUploadReturn {
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null)
  const [quotaStatus, setQuotaStatus] = useState<QuotaStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentUploadId, setCurrentUploadId] = useState<string | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // 업로드 시작
  const uploadVideo = useCallback(async (file: File, metadata: VideoMetadata) => {
    try {
      setError(null)
      setIsUploading(true)
      setProgress(0)

      // 1. 할당량 확인
      const canUpload = await youtubeUploader.canUpload()
      if (!canUpload.allowed) {
        throw new Error(canUpload.reason)
      }

      // 2. 업로드 시작
      const response = await youtubeUploader.uploadVideo(file, metadata)
      setCurrentUploadId(response.upload_id)

      // 3. 진행률 폴링 시작
      startProgressPolling(response.upload_id)

    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 실패')
      setIsUploading(false)
    }
  }, [])

  // 진행률 폴링
  const startProgressPolling = useCallback((uploadId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await youtubeUploader.getUploadStatus(uploadId)
        setUploadStatus(status)
        setProgress(status.progress)

        // 업로드 완료 또는 실패 시 폴링 중단
        if (status.status === 'completed' || status.status === 'failed') {
          setIsUploading(false)
          clearInterval(interval)
          setPollingInterval(null)

          if (status.status === 'failed') {
            setError(status.error || '업로드 실패')
          }
        }

      } catch (err) {
        console.error('상태 조회 실패:', err)
      }
    }, 2000) // 2초마다 폴링

    setPollingInterval(interval)
  }, [])

  // 업로드 취소
  const cancelUpload = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
    setIsUploading(false)
    setCurrentUploadId(null)
    setUploadStatus(null)
    setProgress(0)
  }, [pollingInterval])

  // 할당량 상태 확인
  const checkQuota = useCallback(async () => {
    try {
      const quota = await youtubeUploader.getQuotaStatus()
      setQuotaStatus(quota)
    } catch (err) {
      console.error('할당량 조회 실패:', err)
    }
  }, [])

  // 에러 초기화
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // 컴포넌트 언마운트 시 폴링 정리
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  // 마운트 시 할당량 상태 확인
  useEffect(() => {
    checkQuota()
  }, [checkQuota])

  return {
    isUploading,
    progress,
    uploadStatus,
    quotaStatus,
    error,
    uploadVideo,
    cancelUpload,
    checkQuota,
    clearError
  }
}
```

#### 2.3 YouTube 업로드 모달 컴포넌트

**src/components/upload/YouTubeUploadModal.tsx**
```typescript
'use client'

import React, { useState } from 'react'
import { useYouTubeUpload } from '@/hooks/useYouTubeUpload'
import Modal from '@/components/ui/Modal'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import ProgressBar from '@/components/ui/ProgressBar'
import { FaYoutube, FaCheck, FaExternalLinkAlt } from 'react-icons/fa'

interface YouTubeUploadModalProps {
  isOpen: boolean
  onClose: () => void
  videoFile?: File
  videoUrl?: string
  defaultTitle?: string
}

export default function YouTubeUploadModal({
  isOpen,
  onClose,
  videoFile,
  videoUrl,
  defaultTitle = ''
}: YouTubeUploadModalProps) {
  const {
    isUploading,
    progress,
    uploadStatus,
    quotaStatus,
    error,
    uploadVideo,
    cancelUpload,
    clearError
  } = useYouTubeUpload()

  const [metadata, setMetadata] = useState({
    title: defaultTitle,
    description: '',
    tags: [] as string[],
    privacy: 'private' as 'private' | 'unlisted' | 'public'
  })
  const [tagsInput, setTagsInput] = useState('')

  // 업로드 시작
  const handleUpload = async () => {
    if (!videoFile && !videoUrl) {
      alert('업로드할 비디오가 없습니다.')
      return
    }

    if (!metadata.title.trim()) {
      alert('제목을 입력해주세요.')
      return
    }

    try {
      let file = videoFile

      // URL에서 파일 다운로드 (GPU 렌더링된 경우)
      if (!file && videoUrl) {
        const response = await fetch(videoUrl)
        const blob = await response.blob()
        file = new File([blob], 'video.mp4', { type: 'video/mp4' })
      }

      if (!file) {
        throw new Error('파일을 준비할 수 없습니다.')
      }

      // 태그 파싱
      const tags = tagsInput
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0)

      await uploadVideo(file, {
        ...metadata,
        tags
      })

    } catch (err) {
      console.error('업로드 실패:', err)
    }
  }

  // 모달 닫기
  const handleClose = () => {
    if (isUploading) {
      if (confirm('업로드를 취소하시겠습니까?')) {
        cancelUpload()
        onClose()
      }
    } else {
      onClose()
    }
  }

  // 완료 상태인지 확인
  const isCompleted = uploadStatus?.status === 'completed'
  const isFailed = uploadStatus?.status === 'failed'

  return (
    <Modal isOpen={isOpen} onClose={handleClose} className="max-w-lg">
      <div className="p-6">
        {/* 헤더 */}
        <div className="flex items-center gap-3 mb-6">
          <FaYoutube className="text-red-500 text-2xl" />
          <h2 className="text-xl font-bold">YouTube 업로드</h2>
        </div>

        {/* 할당량 상태 */}
        {quotaStatus && (
          <div className="mb-4 p-3 bg-gray-100 rounded-lg">
            <div className="text-sm text-gray-600">
              일일 할당량: {quotaStatus.used.toLocaleString()} / {quotaStatus.limit.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600">
              남은 할당량: {quotaStatus.remaining.toLocaleString()}
              {quotaStatus.remaining < 1600 && (
                <span className="text-red-500 ml-2">⚠️ 업로드 불가 (1600 필요)</span>
              )}
            </div>
          </div>
        )}

        {/* 업로드 완료 */}
        {isCompleted && uploadStatus && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <FaCheck className="text-green-500" />
              <span className="font-medium text-green-700">업로드 완료!</span>
            </div>

            <div className="space-y-2">
              <a
                href={uploadStatus.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-blue-600 hover:text-blue-800"
              >
                <FaExternalLinkAlt className="text-sm" />
                YouTube에서 보기
              </a>

              <a
                href={uploadStatus.studio_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-blue-600 hover:text-blue-800"
              >
                <FaExternalLinkAlt className="text-sm" />
                YouTube Studio에서 편집
              </a>
            </div>
          </div>
        )}

        {/* 에러 표시 */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-700">{error}</div>
            <Button
              variant="text"
              size="sm"
              onClick={clearError}
              className="mt-2 text-red-600"
            >
              닫기
            </Button>
          </div>
        )}

        {/* 진행률 */}
        {isUploading && (
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">업로드 진행률</span>
              <span className="text-sm text-gray-600">{progress}%</span>
            </div>
            <ProgressBar progress={progress} />
          </div>
        )}

        {/* 메타데이터 입력 폼 */}
        {!isCompleted && (
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                제목 <span className="text-red-500">*</span>
              </label>
              <Input
                value={metadata.title}
                onChange={(e) => setMetadata(prev => ({ ...prev, title: e.target.value }))}
                placeholder="비디오 제목을 입력하세요"
                maxLength={100}
                disabled={isUploading}
              />
              <div className="text-xs text-gray-500 mt-1">
                {metadata.title.length}/100
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">설명</label>
              <textarea
                value={metadata.description}
                onChange={(e) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
                placeholder="비디오 설명을 입력하세요"
                className="w-full p-3 border border-gray-300 rounded-lg resize-none"
                rows={4}
                maxLength={5000}
                disabled={isUploading}
              />
              <div className="text-xs text-gray-500 mt-1">
                {metadata.description.length}/5000
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">태그</label>
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="태그를 쉼표로 구분하여 입력하세요"
                disabled={isUploading}
              />
              <div className="text-xs text-gray-500 mt-1">
                예: ECG, 자막, 편집
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">공개 설정</label>
              <select
                value={metadata.privacy}
                onChange={(e) => setMetadata(prev => ({
                  ...prev,
                  privacy: e.target.value as 'private' | 'unlisted' | 'public'
                }))}
                className="w-full p-3 border border-gray-300 rounded-lg"
                disabled={isUploading}
              >
                <option value="private">비공개</option>
                <option value="unlisted">링크만 공유</option>
                <option value="public">공개</option>
              </select>
            </div>
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="flex gap-3">
          {isCompleted ? (
            <Button
              variant="primary"
              onClick={onClose}
              className="flex-1"
            >
              완료
            </Button>
          ) : (
            <>
              <Button
                variant="secondary"
                onClick={handleClose}
                disabled={isUploading}
                className="flex-1"
              >
                취소
              </Button>

              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={
                  isUploading ||
                  !metadata.title.trim() ||
                  (quotaStatus && quotaStatus.remaining < 1600)
                }
                className="flex-1"
              >
                {isUploading ? '업로드 중...' : 'YouTube 업로드'}
              </Button>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}
```

#### 2.1 GPU 렌더링과 연결

**GPU 렌더링 완료 시 download_url을 YouTube 업로드로 연결**
```typescript
// 기존 imports에 추가
import YouTubeUploadModal from '@/components/upload/YouTubeUploadModal'
import { FaYoutube } from 'react-icons/fa'

// 기존 컴포넌트에 상태 추가
const [showYouTubeUpload, setShowYouTubeUpload] = useState(false)

// 렌더링 완료 시 YouTube 버튼 활성화
const isRenderCompleted = status === 'completed' && downloadUrl

// YouTube 업로드 핸들러
const handleYouTubeUpload = () => {
  setShowYouTubeUpload(true)
}

// JSX에 버튼 추가 (완료 상태에서)
{isRenderCompleted && (
  <div className="flex gap-3 mt-4">
    <Button
      variant="primary"
      onClick={downloadFile}
      className="flex-1"
    >
      <FaDownload className="mr-2" />
      다운로드
    </Button>

    <Button
      variant="secondary"
      onClick={handleYouTubeUpload}
      className="flex-1 bg-red-500 hover:bg-red-600 text-white"
    >
      <FaYoutube className="mr-2" />
      YouTube 업로드
    </Button>
  </div>
)}

// 모달 추가 (컴포넌트 하단)
<YouTubeUploadModal
  isOpen={showYouTubeUpload}
  onClose={() => setShowYouTubeUpload(false)}
  videoUrl={downloadUrl}
  defaultTitle={videoName || ''}
/>
```

## 🧪 테스트 시나리오

### 기본 테스트 (Phase 1)

1. **friends.mp4 파일 업로드 테스트**
   ```bash
   # 1. 백엔드 서버 실행
   uvicorn app.main:app --reload

   # 2. friends.mp4 파일로 테스트
   curl -X POST "http://localhost:8000/api/youtube/upload" \
     -F "file=@friends.mp4" \
     -F "metadata_json={\"title\":\"ECG 테스트\",\"privacy\":\"private\"}" \
     -H "Authorization: Bearer your_token"

   # 3. 진행률 확인
   curl "http://localhost:8000/api/youtube/status/{upload_id}"

   # 4. 할당량 상태 확인
   curl "http://localhost:8000/api/youtube/quota" \
     -H "Authorization: Bearer your_token"
   ```

2. **핵심 검증 항목**
   - ✅ 할당량 관리 (1600 quota per upload)
   - ✅ 실시간 진행률 추적
   - ✅ YouTube Studio 링크 생성
   - ✅ 에러 처리 및 재시도

### 확장 테스트 (Phase 2)

1. **GPU 렌더링 통합 테스트**
   ```bash
   # GPU 렌더링 완료 → download_url → YouTube 업로드
   curl -X POST "http://localhost:8000/api/youtube/upload" \
     -H "Content-Type: application/json" \
     -d '{"videoUrl":"gpu_download_url","metadata":{...}}'
   ```

## 🎯 구현 우선순위

### Phase 1: 핵심 기능 (필수)
1. ✅ friends.mp4 파일 업로드
2. ✅ YouTube API 연동
3. ✅ 할당량 관리
4. ✅ 진행률 추적

### Phase 2: 확장 기능 (선택)
1. 🔄 GPU 렌더링 통합
2. 🔄 URL 다운로드 업로드
3. 🔄 프론트엔드 UI 개선

## 🔧 주요 파일 구조

### 새로 생성할 파일들
```
backend/
├── services/youtube_service.py
├── routers/youtube.py
└── requirements.txt (수정)

frontend/
├── src/lib/youtube/YouTubeUploader.ts
├── src/hooks/useYouTubeUpload.ts
├── src/components/upload/YouTubeUploadModal.tsx
└── .env (수정)
```

### 수정할 기존 파일들
```
frontend/
└── src/app/(route)/editor/components/Export/ServerVideoExportModal.tsx
```

## 📊 예상 성과

### 기술적 성과
- ✅ **컴파일 에러 없는 깨끗한 코드**
- ✅ **실제 YouTube API 스펙 준수**
- ✅ **간단하고 디버깅 가능한 구조**
- ✅ **빠른 구현 (3-4일)**

### 사용자 경험
- **직관적인 업로드 플로우**
- **실시간 진행률 표시**
- **할당량 상태 투명성**
- **원클릭 YouTube Studio 접근**

### 할당량 관리
- **기본적인 할당량 확인** (1600 tokens)
- **하루 최대 6개 업로드** (10,000 ÷ 1600)
- **투명한 사용량 표시**
- **점진적 최적화 가능**

## ⚠️ 중요 주의사항

1. **OAuth 인증**: Google Cloud Console에서 올바른 리다이렉션 URI 설정 필요
2. **파일 크기**: 대용량 파일 업로드 시 청크 업로드 구현
3. **보안**: 토큰을 안전하게 저장하고 만료 시 자동 갱신
4. **에러 처리**: 명확한 에러 메시지와 복구 방법 제시

---

## 📈 기대 효과

### 즉시 테스트 가능
- ✅ friends.mp4로 바로 YouTube 업로드 검증
- ✅ 복잡한 GPU 렌더링 없이 API 기능 확인
- ✅ 할당량 관리, 진행률, 에러 처리 모두 테스트

### 점진적 확장
- 🔄 파일 업로드 방식 검증 완료 후
- 🔄 GPU 렌더링 URL 방식 추가
- 🔄 프론트엔드 통합 및 UI 개선

이 가이드를 따라 구현하면 **단계별로 검증 가능한 YouTube 업로드 기능**을 안전하게 구축할 수 있습니다. friends.mp4 테스트로 기본 기능을 완전히 검증한 후, GPU 렌더링과의 통합을 진행하는 것이 가장 효율적인 접근 방식입니다.
