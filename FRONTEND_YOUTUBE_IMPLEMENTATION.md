# 프론트엔드 YouTube 업로드 구현 가이드

백엔드 YouTube API가 완료되었습니다 (PostgreSQL 기반 할당량 관리 포함). 이제 프론트엔드에서 사용할 수 있는 YouTube 업로드 클라이언트, 훅, 컴포넌트를 구현해야 합니다.

**우선 목표**: friends.mp4 파일 선택 및 업로드 기능 구현 후 GPU 렌더링과 통합

## 백엔드 API 엔드포인트 (완료됨)

- `GET /api/youtube/auth/url` - YouTube OAuth 인증 URL 생성
- `POST /api/youtube/upload` - 비디오 업로드 시작
- `GET /api/youtube/status/{upload_id}` - 업로드 진행률 조회
- `GET /api/youtube/quota` - 할당량 상태 조회 (PostgreSQL 기반)
- `DELETE /api/youtube/cancel/{upload_id}` - 업로드 취소

**할당량 관리**: PostgreSQL 데이터베이스 기반으로 일일 할당량 추적 (Redis 대신)

## 구현 계획

### Phase 1: 기본 파일 업로드 (우선 구현)
- friends.mp4 파일 선택 및 업로드
- 기본 YouTube 업로드 기능 검증
- 메타데이터 입력 및 진행률 추적

### Phase 2: GPU 렌더링 통합 (확장 기능)
- 렌더링 완료 시 자동 YouTube 업로드
- 기존 파일 업로드 로직 재사용

## Phase 1: 기본 파일 업로드 구현

### Phase 2.1: YouTube API 클라이언트

**파일: `src/lib/youtube/YouTubeUploader.ts`**

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
  status: 'preparing' | 'uploading' | 'completed' | 'failed' | 'cancelled'
  progress: number
  video_id?: string
  video_url?: string
  studio_url?: string
  error?: string
  created_at?: string
  completed_at?: string
}

interface QuotaStatus {
  used: number
  limit: number
  remaining: number
  can_upload: boolean
  uploads_available: number
}

class YouTubeUploader {
  private baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

  /**
   * YouTube 인증 URL 가져오기
   */
  async getAuthUrl(): Promise<{ auth_url: string; message: string }> {
    const token = this.getAuthToken()
    if (!token) {
      throw new Error('인증 토큰이 없습니다')
    }

    const response = await fetch(`${this.baseURL}/api/youtube/auth/url`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'YouTube 인증 URL 생성 실패')
    }

    return response.json()
  }

  /**
   * 비디오 업로드 시작 (파일) - Phase 1 우선 구현
   */
  async uploadVideoFile(file: File, metadata: VideoMetadata): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata_json', JSON.stringify(metadata))

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
   * 비디오 업로드 시작 (URL) - Phase 2 확장 기능
   */
  async uploadVideoUrl(videoUrl: string, metadata: VideoMetadata): Promise<UploadResponse> {
    const token = this.getAuthToken()
    if (!token) {
      throw new Error('인증 토큰이 없습니다')
    }

    const response = await fetch(`${this.baseURL}/api/youtube/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        videoUrl,
        metadata
      })
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
      const error = await response.json()
      throw new Error(error.detail || '상태 조회 실패')
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
      const error = await response.json()
      throw new Error(error.detail || '할당량 조회 실패')
    }

    return response.json()
  }

  /**
   * 업로드 취소
   */
  async cancelUpload(uploadId: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseURL}/api/youtube/cancel/${uploadId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '취소 실패')
    }

    return response.json()
  }

  /**
   * 할당량 확인 (업로드 가능 여부)
   */
  async canUpload(): Promise<{ allowed: boolean; reason?: string }> {
    try {
      const quota = await this.getQuotaStatus()

      if (!quota.can_upload) {
        return {
          allowed: false,
          reason: `할당량 부족 (남은 할당량: ${quota.remaining}/1600 필요) - PostgreSQL 기반 추적`
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

### Phase 2.2: React 훅 구현

**파일: `src/hooks/useYouTubeUpload.ts`**

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
  uploadVideoFile: (file: File, metadata: VideoMetadata) => Promise<void>
  uploadVideoUrl: (videoUrl: string, metadata: VideoMetadata) => Promise<void>
  cancelUpload: () => void
  checkQuota: () => Promise<void>
  clearError: () => void
  getAuthUrl: () => Promise<string>
}

export function useYouTubeUpload(): UseYouTubeUploadReturn {
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null)
  const [quotaStatus, setQuotaStatus] = useState<QuotaStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentUploadId, setCurrentUploadId] = useState<string | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // 파일 업로드
  const uploadVideoFile = useCallback(async (file: File, metadata: VideoMetadata) => {
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
      const response = await youtubeUploader.uploadVideoFile(file, metadata)
      setCurrentUploadId(response.upload_id)

      // 3. 진행률 폴링 시작
      startProgressPolling(response.upload_id)

    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 실패')
      setIsUploading(false)
    }
  }, [])

  // URL 업로드
  const uploadVideoUrl = useCallback(async (videoUrl: string, metadata: VideoMetadata) => {
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
      const response = await youtubeUploader.uploadVideoUrl(videoUrl, metadata)
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
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
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
  const cancelUpload = useCallback(async () => {
    if (currentUploadId) {
      try {
        await youtubeUploader.cancelUpload(currentUploadId)
      } catch (err) {
        console.error('취소 실패:', err)
      }
    }

    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
    setIsUploading(false)
    setCurrentUploadId(null)
    setUploadStatus(null)
    setProgress(0)
  }, [currentUploadId, pollingInterval])

  // 할당량 상태 확인
  const checkQuota = useCallback(async () => {
    try {
      const quota = await youtubeUploader.getQuotaStatus()
      setQuotaStatus(quota)
    } catch (err) {
      console.error('할당량 조회 실패:', err)
    }
  }, [])

  // YouTube 인증 URL 가져오기
  const getAuthUrl = useCallback(async () => {
    try {
      const response = await youtubeUploader.getAuthUrl()
      return response.auth_url
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'YouTube 인증 URL 가져오기 실패')
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
    uploadVideoFile,
    uploadVideoUrl,
    cancelUpload,
    checkQuota,
    clearError,
    getAuthUrl
  }
}
```

### Phase 2.3: YouTube 업로드 모달 컴포넌트

**파일: `src/components/upload/YouTubeUploadModal.tsx`**

```typescript
'use client'

import React, { useState } from 'react'
import { useYouTubeUpload } from '@/hooks/useYouTubeUpload'
import { FaYoutube, FaCheck, FaExternalLinkAlt, FaSpinner } from 'react-icons/fa'

interface YouTubeUploadModalProps {
  isOpen: boolean
  onClose: () => void
  videoFile?: File              // Phase 1: 파일 업로드 우선
  videoUrl?: string            // Phase 2: GPU 렌더링 확장
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
    uploadVideoFile,
    uploadVideoUrl,
    cancelUpload,
    clearError,
    getAuthUrl
  } = useYouTubeUpload()

  const [metadata, setMetadata] = useState({
    title: defaultTitle,
    description: '',
    tags: [] as string[],
    privacy: 'private' as 'private' | 'unlisted' | 'public'
  })
  const [tagsInput, setTagsInput] = useState('')
  const [needsAuth, setNeedsAuth] = useState(false)
  const [authUrl, setAuthUrl] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(videoFile || null)

  // YouTube 인증 체크
  const checkAuthAndUpload = async () => {
    try {
      await handleUpload()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '업로드 실패'

      // 인증이 필요한 경우
      if (errorMessage.includes('인증') || errorMessage.includes('토큰')) {
        setNeedsAuth(true)
        try {
          const url = await getAuthUrl()
          setAuthUrl(url)
        } catch (authErr) {
          console.error('YouTube 인증 URL 가져오기 실패:', authErr)
        }
      }
    }
  }

  // 업로드 시작
  const handleUpload = async () => {
    if (!metadata.title.trim()) {
      alert('제목을 입력해주세요.')
      return
    }

    // 태그 파싱
    const tags = tagsInput
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)

    const uploadMetadata = {
      ...metadata,
      tags
    }

    try {
      // Phase 1: 파일 업로드 우선 처리
      if (selectedFile) {
        await uploadVideoFile(selectedFile, uploadMetadata)
      } else if (videoUrl) {
        // Phase 2: GPU 렌더링 URL 처리
        await uploadVideoUrl(videoUrl, uploadMetadata)
      } else {
        throw new Error('업로드할 비디오 파일을 선택하거나 GPU 렌더링 URL이 필요합니다.')
      }
    } catch (err) {
      console.error('업로드 실패:', err)
      throw err
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

  // YouTube 인증 페이지로 이동
  const handleYouTubeAuth = () => {
    if (authUrl) {
      window.open(authUrl, '_blank')
    }
  }

  // 완료 상태인지 확인
  const isCompleted = uploadStatus?.status === 'completed'
  const isFailed = uploadStatus?.status === 'failed'

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* 헤더 */}
          <div className="flex items-center gap-3 mb-6">
            <FaYoutube className="text-red-500 text-2xl" />
            <h2 className="text-xl font-bold">YouTube 업로드</h2>
          </div>

          {/* YouTube 인증 필요 */}
          {needsAuth && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <FaYoutube className="text-yellow-500" />
                <span className="font-medium text-yellow-700">YouTube 인증이 필요합니다</span>
              </div>
              <p className="text-sm text-yellow-600 mb-3">
                YouTube에 업로드하려면 먼저 계정 연동이 필요합니다.
              </p>
              <button
                onClick={handleYouTubeAuth}
                className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 flex items-center gap-2"
              >
                <FaYoutube />
                YouTube 계정 연동
              </button>
            </div>
          )}

          {/* 할당량 상태 */}
          {quotaStatus && (
            <div className="mb-4 p-3 bg-gray-100 rounded-lg">
              <div className="text-sm text-gray-600">
                일일 할당량: {quotaStatus.used.toLocaleString()} / {quotaStatus.limit.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600">
                남은 업로드 가능 횟수: {quotaStatus.uploads_available}회
                {!quotaStatus.can_upload && (
                  <span className="text-red-500 ml-2">⚠️ 업로드 불가</span>
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
          {error && !needsAuth && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="text-red-700">{error}</div>
              <button
                onClick={clearError}
                className="mt-2 text-red-600 text-sm hover:underline"
              >
                닫기
              </button>
            </div>
          )}

          {/* 진행률 */}
          {isUploading && (
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">업로드 진행률</span>
                <span className="text-sm text-gray-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* 파일 선택 - Phase 1 우선 구현 */}
          {!isCompleted && !needsAuth && !videoUrl && (
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                비디오 파일 선택 <span className="text-red-500">*</span>
              </label>
              <input
                type="file"
                accept="video/*"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    setSelectedFile(file)
                    if (!metadata.title) {
                      setMetadata(prev => ({ ...prev, title: file.name.replace(/\.[^/.]+$/, "") }))
                    }
                  }
                }}
                disabled={isUploading}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {selectedFile && (
                <div className="text-sm text-gray-600 mt-1">
                  선택된 파일: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </div>
              )}
            </div>
          )}

          {/* 메타데이터 입력 폼 */}
          {!isCompleted && !needsAuth && (selectedFile || videoUrl) && (
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-2">
                  제목 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={metadata.title}
                  onChange={(e) => setMetadata(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="비디오 제목을 입력하세요"
                  maxLength={100}
                  disabled={isUploading}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="태그를 쉼표로 구분하여 입력하세요"
                  disabled={isUploading}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              <button
                onClick={onClose}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
              >
                완료
              </button>
            ) : needsAuth ? (
              <>
                <button
                  onClick={onClose}
                  className="flex-1 bg-gray-500 text-white py-2 px-4 rounded-lg hover:bg-gray-600 transition-colors"
                >
                  취소
                </button>
                <button
                  onClick={() => {
                    setNeedsAuth(false)
                    setAuthUrl(null)
                  }}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  다시 시도
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleClose}
                  disabled={isUploading}
                  className="flex-1 bg-gray-500 text-white py-2 px-4 rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50"
                >
                  취소
                </button>

                <button
                  onClick={checkAuthAndUpload}
                  disabled={
                    isUploading ||
                    !metadata.title.trim() ||
                    (!selectedFile && !videoUrl) ||
                    (quotaStatus && !quotaStatus.can_upload)
                  }
                  className="flex-1 bg-red-500 text-white py-2 px-4 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      업로드 중...
                    </>
                  ) : (
                    <>
                      <FaYoutube />
                      YouTube 업로드
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

## Phase 2: GPU 렌더링 통합 (확장 기능)

기존 ServerVideoExportModal에 YouTube 업로드 버튼을 추가하는 예시입니다:

**파일 수정: `src/app/(route)/editor/components/Export/ServerVideoExportModal.tsx`**

```typescript
// 기존 imports에 추가
import YouTubeUploadModal from '@/components/upload/YouTubeUploadModal'
import { FaYoutube, FaDownload } from 'react-icons/fa'

// 컴포넌트 내부에 상태 추가
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
    <button
      onClick={downloadFile}
      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
    >
      <FaDownload />
      다운로드
    </button>

    <button
      onClick={handleYouTubeUpload}
      className="flex-1 bg-red-500 text-white py-2 px-4 rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
    >
      <FaYoutube />
      YouTube 업로드
    </button>
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

## 환경 변수 설정

**프론트엔드 .env 파일에 추가:**

```bash
# YouTube API 설정
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# 기존 Google OAuth 설정 활용
NEXT_PUBLIC_GOOGLE_CLIENT_ID=1076942061297-flpl289j4gi2a96ed8do37j16b9hcu97.apps.googleusercontent.com
```

## 구현 순서 및 특징

### Phase 1: 기본 파일 업로드 (우선 구현)
1. **파일 선택 UI**: friends.mp4 파일 선택 및 미리보기
2. **간단한 API 클라이언트**: 복잡한 최적화 없이 기본 기능에 집중
3. **실시간 진행률**: 2초마다 폴링하여 업로드 상태 업데이트
4. **할당량 관리**: 업로드 전 할당량 확인 및 상태 표시
5. **OAuth 인증**: YouTube 인증이 필요한 경우 자동으로 안내

### Phase 2: GPU 렌더링 통합 (확장 기능)
1. **렌더링 연결**: GPU 렌더링 완료 후 바로 YouTube 업로드
2. **URL 처리**: download_url 자동 처리
3. **통합 인터페이스**: 파일 업로드와 동일한 UI 재사용

## 📊 테스트 시나리오

### Phase 1 테스트
```bash
# 1. friends.mp4 파일 선택
# 2. 메타데이터 입력 (제목, 설명, 태그)
# 3. YouTube 업로드 시작
# 4. 진행률 확인
# 5. YouTube Studio 링크 확인
```

### Phase 2 테스트
```bash
# 1. GPU 렌더링 완료
# 2. 자동으로 YouTube 업로드 버튼 활성화
# 3. 메타데이터 입력 후 업로드
```

이 단계별 구현으로 **검증된 YouTube 업로드 기능**을 프론트엔드에서 안전하게 사용할 수 있습니다. friends.mp4 테스트로 기본 기능을 완전히 검증한 후, GPU 렌더링과의 통합을 진행합니다.