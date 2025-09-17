# Frontend-Backend API 통합 가이드

## 📋 목차
1. [서버 정보](#서버-정보)
2. [인증 시스템](#인증-시스템)
3. [비디오 처리 API](#비디오-처리-api)
4. [프로젝트 관리 API](#프로젝트-관리-api)
5. [에러 처리](#에러-처리)
6. [TypeScript 인터페이스](#typescript-인터페이스)
7. [React 구현 예시](#react-구현-예시)

---

## 서버 정보

### 환경별 URL
```yaml
# Production
API_BASE_URL: https://ho-it.site
FRONTEND_URL: https://d31nzc58rhgh3i.cloudfront.net

# Development
API_BASE_URL: http://localhost:8000
FRONTEND_URL: http://localhost:3000
```

### CORS 허용 도메인
- `http://localhost:3000`
- `https://d31nzc58rhgh3i.cloudfront.net`
- `https://ho-it.site`

---

## 인증 시스템

### 📌 회원가입
```http
POST /api/auth/signup
Content-Type: application/json

{
    "username": "john_doe",      // 3-50자
    "email": "john@example.com",
    "password": "SecurePass123!"  // 최소 8자
}
```

**응답 (201 Created)**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "auth_provider": "local",
        "is_active": true,
        "is_verified": false,
        "created_at": "2024-01-15T10:30:00Z"
    }
}
// + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax
```

### 📌 로그인
```http
POST /api/auth/login
Content-Type: application/json

{
    "email": "john@example.com",
    "password": "SecurePass123!"
}
```

**응답 (200 OK)**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": { /* User 객체 */ }
}
```

### 📌 사용자 정보 조회
```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

**응답 (200 OK)**
```json
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "auth_provider": "local",
    "is_active": true,
    "is_verified": true,
    "created_at": "2024-01-15T10:30:00Z"
}
```

### 📌 Google OAuth
```http
# 1. 로그인 페이지로 리다이렉트
GET /api/auth/google/login

# 2. 콜백 처리 (자동)
GET /api/auth/google/callback?code=...
→ 프론트엔드로 리다이렉트 with 토큰
```

### 📌 토큰 갱신
```http
POST /api/auth/refresh
Cookie: refresh_token={refresh_token}
```

**응답 (200 OK)**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
}
```

### 📌 로그아웃
```http
POST /api/auth/logout
Authorization: Bearer {access_token}
```

---

## 비디오 처리 API

### 📌 S3 업로드 URL 생성
```http
POST /api/upload-video/generate-url
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "file_name": "my_video.mp4",
    "file_type": "video/mp4"
}
```

**응답 (200 OK)**
```json
{
    "upload_url": "https://s3.amazonaws.com/...",
    "file_key": "videos/2024/01/550e8400.mp4",
    "expires_at": "2024-01-15T11:30:00Z"
}
```

### 📌 ML 처리 요청
```http
POST /api/upload-video/request-process
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "file_key": "videos/2024/01/550e8400.mp4",
    "language": "ko"  // Optional: "auto"|"ko"|"en"|"ja"|"zh"
}
```

**응답 (200 OK)**
```json
{
    "message": "Video processing started.",
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 📌 처리 상태 조회
```http
GET /api/upload-video/status/{job_id}
Authorization: Bearer {access_token}
```

**응답 - 처리 중**
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "progress": 60
}
```

**응답 - 완료**
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress": 100,
    "result": {
        "segments": [
            {
                "start_time": 1.5,
                "end_time": 3.2,
                "text": "안녕하세요",
                "speaker": {"speaker_id": "SPEAKER_00"},
                "words": [
                    {
                        "word": "안녕하세요",
                        "start": 1.5,
                        "end": 1.8,
                        "acoustic_features": {
                            "volume_db": -20.0,
                            "pitch_hz": 150.0
                        }
                    }
                ]
            }
        ],
        "word_segments": [
            {
                "word": "안녕하세요",
                "start_time": 1.5,
                "end_time": 1.8,
                "speaker_id": "SPEAKER_00",
                "confidence": 0.95
            }
        ],
        "text": "안녕하세요 오늘은 좋은 하루입니다",
        "language": "ko",
        "duration": 120.5,
        "speakers": {
            "SPEAKER_00": {
                "total_duration": 45.2,
                "segment_count": 12
            }
        },
        "metadata": {
            "model_version": "whisperx-base",
            "processing_time": 45.2,
            "unique_speakers": 2,
            "total_segments": 35
        }
    }
}
```

### 비디오 처리 플로우
```
1. Frontend → S3 업로드 URL 요청
2. Frontend → S3 직접 업로드
3. Frontend → ML 처리 요청 (file_key 전달)
4. Backend → ML Server로 분석 요청
5. Frontend → 3초 간격으로 상태 폴링
6. Backend → 완료 시 결과 반환
```

---

## 프로젝트 관리 API

### 📌 프로젝트 생성/업데이트
```http
PUT /api/projects/{project_id}
Authorization: Bearer {access_token}
If-Match: 3  // 버전 충돌 방지 (선택적)
Content-Type: application/json

{
    "id": "project_123",
    "name": "My Video Project",
    "video_url": "https://s3.amazonaws.com/...",
    "clips": [
        {
            "id": "clip_1",
            "start_time": 0,
            "end_time": 3.5,
            "text": "안녕하세요",
            "words": [/*...*/]
        }
    ],
    "settings": {
        "font_size": 24,
        "font_family": "Noto Sans KR",
        "position": "bottom",
        "color": "#FFFFFF"
    },
    "updated_at": "2024-01-15T10:30:00Z",
    "version": 3
}
```

**응답 - 성공 (200 OK)**
```json
{
    "id": "project_123",
    "version": 4,
    "updated_at": "2024-01-15T10:30:00Z",
    "sync_status": "synced"
}
```

**응답 - 충돌 (409 Conflict)**
```json
{
    "error": "CONFLICT",
    "message": "Version conflict detected",
    "current_version": 5,
    "your_version": 3
}
```

### 📌 프로젝트 조회
```http
GET /api/projects/{project_id}
Authorization: Bearer {access_token}
```

### 📌 프로젝트 목록
```http
GET /api/projects?page=1&limit=20&sort=updated_at:desc
Authorization: Bearer {access_token}
```

**응답 (200 OK)**
```json
{
    "data": [
        {
            "id": "project_123",
            "name": "My Video Project",
            "thumbnail_url": "https://s3.amazonaws.com/...",
            "duration": 120.5,
            "created_at": "2024-01-14T10:00:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "sync_status": "synced"
        }
    ],
    "pagination": {
        "page": 1,
        "limit": 20,
        "total_pages": 5,
        "total_items": 95
    }
}
```

### 📌 프로젝트 삭제
```http
DELETE /api/projects/{project_id}
Authorization: Bearer {access_token}
```

---

## 에러 처리

### HTTP 상태 코드
| 코드 | 의미 | 처리 방법 |
|-----|------|----------|
| 200 | 성공 | 정상 처리 |
| 201 | 생성됨 | 리소스 생성 성공 |
| 204 | 콘텐츠 없음 | 삭제 성공 |
| 400 | 잘못된 요청 | 입력값 검증 |
| 401 | 인증 실패 | 토큰 갱신 또는 재로그인 |
| 403 | 권한 없음 | 권한 확인 |
| 404 | 찾을 수 없음 | 리소스 확인 |
| 409 | 충돌 | 버전 충돌 해결 |
| 422 | 처리 불가 | 데이터 형식 확인 |
| 429 | 요청 과다 | 재시도 대기 |
| 500 | 서버 오류 | 재시도 또는 지원 문의 |

### 에러 응답 형식
```json
{
    "detail": {
        "error": "VALIDATION_ERROR",
        "message": "입력값이 올바르지 않습니다",
        "field_errors": {
            "email": ["유효한 이메일 주소가 아닙니다"],
            "password": ["비밀번호는 최소 8자 이상이어야 합니다"]
        }
    }
}
```

---

## TypeScript 인터페이스

```typescript
// auth.types.ts
export interface AuthTokens {
    access_token: string;
    refresh_token?: string;
    token_type: 'bearer';
}

export interface User {
    id: number;
    username: string;
    email: string;
    auth_provider: 'local' | 'google';
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
}

// video.types.ts
export interface PresignedUrlResponse {
    upload_url: string;
    file_key: string;
    expires_at: string;
}

export interface ProcessVideoRequest {
    file_key: string;
    language?: 'auto' | 'ko' | 'en' | 'ja' | 'zh';
}

export interface JobStatus {
    job_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    result?: TranscriptionResult;
    error_message?: string;
}

export interface TranscriptionResult {
    segments: Segment[];
    word_segments: WordSegment[];
    text: string;
    language: string;
    duration: number;
    speakers: Record<string, SpeakerInfo>;
    metadata: TranscriptionMetadata;
}

// project.types.ts
export interface Project {
    id: string;
    name: string;
    video_url: string;
    clips: Clip[];
    settings: ProjectSettings;
    created_at: string;
    updated_at: string;
    version: number;
    sync_status: 'pending' | 'syncing' | 'synced' | 'failed';
}

export interface Clip {
    id: string;
    start_time: number;
    end_time: number;
    text: string;
    words: Word[];
}

export interface ProjectSettings {
    font_size: number;
    font_family: string;
    position: 'top' | 'center' | 'bottom';
    color: string;
    background_color?: string;
    background_opacity?: number;
}
```

---

## React 구현 예시

### API 클라이언트 설정
```typescript
// api/client.ts
import axios, { AxiosInstance } from 'axios';

class ApiClient {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://ho-it.site',
            timeout: 30000,
        });

        this.setupInterceptors();
    }

    private setupInterceptors() {
        // 요청 인터셉터 - 토큰 자동 추가
        this.client.interceptors.request.use((config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });

        // 응답 인터셉터 - 401 처리
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    // 토큰 갱신 시도 또는 로그아웃
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }
        );
    }

    async get<T>(url: string): Promise<T> {
        const response = await this.client.get<T>(url);
        return response.data;
    }

    async post<T>(url: string, data?: any): Promise<T> {
        const response = await this.client.post<T>(url, data);
        return response.data;
    }

    async put<T>(url: string, data?: any): Promise<T> {
        const response = await this.client.put<T>(url, data);
        return response.data;
    }

    async delete<T>(url: string): Promise<T> {
        const response = await this.client.delete<T>(url);
        return response.data;
    }
}

export const apiClient = new ApiClient();
```

### 인증 Hook
```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { User, AuthTokens } from '@/types/auth';

export function useAuth() {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setLoading(false);
                return;
            }
            const userData = await apiClient.get<User>('/api/auth/me');
            setUser(userData);
        } catch (error) {
            localStorage.removeItem('access_token');
        } finally {
            setLoading(false);
        }
    };

    const login = async (email: string, password: string) => {
        const response = await apiClient.post<AuthTokens & { user: User }>(
            '/api/auth/login',
            { email, password }
        );
        localStorage.setItem('access_token', response.access_token);
        setUser(response.user);
    };

    const signup = async (username: string, email: string, password: string) => {
        const response = await apiClient.post<AuthTokens & { user: User }>(
            '/api/auth/signup',
            { username, email, password }
        );
        localStorage.setItem('access_token', response.access_token);
        setUser(response.user);
    };

    const logout = async () => {
        try {
            await apiClient.post('/api/auth/logout');
        } finally {
            localStorage.removeItem('access_token');
            setUser(null);
        }
    };

    const googleLogin = () => {
        window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/google/login`;
    };

    return {
        user,
        loading,
        login,
        signup,
        logout,
        googleLogin,
        isAuthenticated: !!user,
    };
}
```

### 비디오 업로드 컴포넌트
```typescript
// components/VideoUpload.tsx
import React, { useState } from 'react';
import { apiClient } from '@/api/client';

export function VideoUpload({ onComplete }) {
    const [uploading, setUploading] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [selectedLanguage, setSelectedLanguage] = useState('ko');

    async function handleFileUpload(file: File) {
        try {
            // 1. S3 업로드 URL 생성
            setUploading(true);
            const { upload_url, file_key } = await apiClient.post(
                '/api/upload-video/generate-url',
                {
                    file_name: file.name,
                    file_type: file.type,
                }
            );

            // 2. S3에 직접 업로드
            await uploadToS3(file, upload_url);
            setUploading(false);

            // 3. ML 처리 요청
            setProcessing(true);
            const { job_id } = await apiClient.post(
                '/api/upload-video/request-process',
                {
                    file_key,
                    language: selectedLanguage,
                }
            );

            // 4. 상태 폴링 (3초 간격)
            await pollJobStatus(job_id);

        } catch (error) {
            console.error('Upload/Processing error:', error);
        } finally {
            setUploading(false);
            setProcessing(false);
        }
    }

    async function uploadToS3(file: File, presignedUrl: string) {
        const xhr = new XMLHttpRequest();

        return new Promise<void>((resolve, reject) => {
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    setProgress(percent);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200 || xhr.status === 204) {
                    resolve();
                } else {
                    reject(new Error(`Upload failed: ${xhr.status}`));
                }
            });

            xhr.addEventListener('error', reject);

            xhr.open('PUT', presignedUrl);
            xhr.setRequestHeader('Content-Type', file.type);
            xhr.send(file);
        });
    }

    async function pollJobStatus(jobId: string) {
        const maxAttempts = 60; // 최대 3분
        const interval = 3000; // 3초

        for (let i = 0; i < maxAttempts; i++) {
            const status = await apiClient.get(`/api/upload-video/status/${jobId}`);
            setProgress(status.progress);

            if (status.status === 'completed') {
                onComplete(status);
                return;
            }

            if (status.status === 'failed') {
                throw new Error(status.error_message || '처리 실패');
            }

            await new Promise(resolve => setTimeout(resolve, interval));
        }

        throw new Error('처리 시간 초과');
    }

    const languages = [
        { code: 'auto', name: '🌐 자동 감지' },
        { code: 'ko', name: '🇰🇷 한국어' },
        { code: 'en', name: '🇺🇸 English' },
        { code: 'ja', name: '🇯🇵 日本語' },
        { code: 'zh', name: '🇨🇳 中文' },
    ];

    return (
        <div>
            {/* 언어 선택 */}
            <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                disabled={uploading || processing}
            >
                {languages.map(lang => (
                    <option key={lang.code} value={lang.code}>
                        {lang.name}
                    </option>
                ))}
            </select>

            {/* 업로드 버튼 */}
            <input
                type="file"
                accept="video/*"
                onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])}
                disabled={uploading || processing}
            />

            {/* 진행률 표시 */}
            {(uploading || processing) && (
                <div>
                    <progress value={progress} max="100" />
                    <span>{progress}%</span>
                </div>
            )}
        </div>
    );
}
```

### 프로젝트 자동 저장
```typescript
// hooks/useProjectAutoSave.ts
import { useCallback, useEffect } from 'react';
import { debounce } from 'lodash';
import { apiClient } from '@/api/client';

export function useProjectAutoSave(projectId: string, projectData: any) {
    const saveProject = useCallback(
        debounce(async (data: any) => {
            try {
                await apiClient.put(`/api/projects/${projectId}`, data, {
                    headers: {
                        'If-Match': data.version
                    }
                });
                console.log('Project saved');
            } catch (error: any) {
                if (error.response?.status === 409) {
                    // 버전 충돌 처리
                    console.error('Version conflict:', error.response.data);
                    // 충돌 해결 로직...
                }
            }
        }, 2000), // 2초 디바운스
        [projectId]
    );

    useEffect(() => {
        if (projectData) {
            saveProject(projectData);
        }
    }, [projectData, saveProject]);
}
```

---

## 📋 체크리스트

### Frontend 구현 체크리스트
- [ ] 환경변수 설정 (`NEXT_PUBLIC_API_URL`)
- [ ] Axios 인터셉터 설정 (토큰 자동 추가)
- [ ] 401 에러 시 자동 로그아웃 처리
- [ ] 파일 업로드 진행률 표시
- [ ] 처리 상태 폴링 구현 (3초 간격)
- [ ] 프로젝트 자동 저장 (2초 디바운스)
- [ ] 버전 충돌 처리 (409 에러)
- [ ] 언어 선택 UI 구현

### 일반적인 문제 해결

#### CORS 에러
```javascript
// next.config.js
module.exports = {
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8000/api/:path*',
            },
        ];
    },
};
```

#### 401 Unauthorized 반복
```javascript
// 토큰 갱신 로직 추가
if (error.response?.status === 401 && !originalRequest._retry) {
    originalRequest._retry = true;
    const newToken = await refreshToken();
    originalRequest.headers.Authorization = `Bearer ${newToken}`;
    return apiClient(originalRequest);
}
```

---

**문서 버전**: 1.0.0
**최종 수정**: 2024-01-15
**작성자**: ECG Backend Team