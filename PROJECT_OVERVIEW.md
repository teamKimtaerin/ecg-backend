# ECG Backend Project Overview

이 문서는 ECG (Expressive Caption Generator) Backend 프로젝트의 전체적인 구현 내용과 작업 히스토리를 정리합니다.

## 프로젝트 개요

**ECG Backend**는 FastAPI 기반의 비디오 분석 및 캡션 생성 서비스 백엔드입니다. AWS 클라우드 환경에서 동작하며, ML 서버와의 통신을 통한 비디오 분석, 사용자 인증, 파일 업로드 등의 기능을 제공합니다.

### 주요 기능
- JWT 기반 사용자 인증 (로컬 + Google OAuth 2.0)
- S3를 이용한 비디오 파일 업로드/다운로드
- ML 서버와의 비동기 통신을 통한 비디오 분석
- 자동 데이터베이스 초기화 및 시드 데이터 생성
- ECS 기반 자동 배포 시스템

## 기술 스택

### Backend Framework
- **FastAPI**: Python 3.11 기반 웹 프레임워크
- **SQLAlchemy 2.0**: ORM 및 데이터베이스 관리
- **PostgreSQL**: 주 데이터베이스
- **Alembic**: 데이터베이스 마이그레이션

### Authentication
- **JWT (PyJWT)**: JSON Web Token 기반 인증
- **Authlib**: Google OAuth 2.0 클라이언트
- **Passlib + BCrypt**: 비밀번호 해싱

### Cloud Services
- **AWS ECS Fargate**: 컨테이너 실행 환경
- **AWS ECR**: Docker 이미지 저장소
- **AWS S3**: 비디오 파일 저장
- **AWS RDS PostgreSQL**: 관리형 데이터베이스

### Development & Deployment
- **Docker**: Multi-stage 컨테이너화
- **GitHub Actions**: CI/CD 파이프라인
- **Ruff, Black, MyPy, Bandit**: 코드 품질 도구

## API 명세

### 인증 관련 API

#### 1. 회원가입
**URL**: `POST /api/auth/signup`

**Request**:
```json
{
  "username": "사용자명",
  "email": "user@example.com",
  "password": "비밀번호"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "사용자명",
    "email": "user@example.com",
    "is_active": true
  }
}
```

#### 2. 로그인
**URL**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "비밀번호"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "사용자명",
    "email": "user@example.com",
    "is_active": true
  }
}
```

#### 3. 사용자 정보 조회
**URL**: `GET /api/auth/me`

**Headers**: `Authorization: Bearer {access_token}`

**Response**:
```json
{
  "id": 1,
  "username": "사용자명",
  "email": "user@example.com",
  "auth_provider": "local",
  "is_active": true,
  "created_at": "2025-09-09T12:00:00Z"
}
```

#### 4. 토큰 갱신
**URL**: `POST /api/auth/refresh`

**Cookies**: `refresh_token`

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 5. 로그아웃
**URL**: `POST /api/auth/logout`

**Response**:
```json
{
  "message": "로그아웃 되었습니다."
}
```

#### 6. Google OAuth 로그인 시작
**URL**: `GET /api/auth/google/login`

**Response**: Google 로그인 페이지로 리다이렉션

#### 7. Google OAuth 콜백
**URL**: `GET /api/auth/google/callback`

**Response**: 프론트엔드로 리다이렉션
- 성공: `/auth/callback?success=true&access_token={token}`
- 실패: `/auth/callback?error={error_message}`

### 파일 업로드 API

#### 8. S3 업로드 URL 생성
**URL**: `POST /api/upload-video/generate-url`

**Request**:
```json
{
  "filename": "video.mp4",
  "content_type": "video/mp4"
}
```

**Response**:
```json
{
  "upload_url": "https://s3.amazonaws.com/bucket/...",
  "file_key": "uploads/uuid/video.mp4",
  "expires_in": 3600
}
```

#### 9. S3 다운로드 URL 생성
**URL**: `GET /api/upload-video/download-url/{file_key}`

**Response**:
```json
{
  "download_url": "https://s3.amazonaws.com/bucket/...",
  "expires_in": 3600
}
```

### ML 서버 통신 API

#### 10. 비디오 분석 요청
**URL**: `POST /api/v1/ml/process-video`

**Headers**: `Authorization: Bearer {access_token}`

**Request**:
```json
{
  "video_file_key": "uploads/uuid/video.mp4",
  "analysis_type": "emotion_analysis"
}
```

**Response**:
```json
{
  "job_id": "ml_job_uuid",
  "status": "processing",
  "message": "비디오 분석이 시작되었습니다."
}
```

#### 11. 분석 상태 조회
**URL**: `GET /api/v1/ml/job-status/{job_id}`

**Headers**: `Authorization: Bearer {access_token}`

**Response**:
```json
{
  "job_id": "ml_job_uuid",
  "status": "completed",
  "progress": 100,
  "result": {
    "captions": [...],
    "emotions": [...],
    "analysis_time": "2025-09-09T12:30:00Z"
  }
}
```

### 헬스 체크 API

#### 12. 헬스 체크
**URL**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "service": "ECG Backend"
}
```

#### 13. 루트 엔드포인트
**URL**: `GET /`

**Response**:
```json
{
  "message": "ECG Backend API",
  "version": "1.0.0"
}
```

#### 14. 테스트 엔드포인트
**URL**: `GET /api/test`

**Response**:
```json
{
  "data": "ECG Backend Test",
  "demo_mode": true
}
```

## 프로젝트 구조

```
ecg-backend/
├── app/
│   ├── main.py                 # FastAPI 애플리케이션 진입점
│   ├── core/
│   │   └── config.py           # 환경변수 및 설정 관리
│   ├── api/v1/
│   │   ├── routers.py          # API 라우터 등록
│   │   ├── auth.py             # 인증 관련 엔드포인트
│   │   ├── video.py            # S3 파일 업로드 API
│   │   └── ml_video.py         # ML 서버 통신 API
│   ├── db/
│   │   ├── database.py         # 데이터베이스 연결 관리
│   │   ├── init_db.py          # 자동 DB 초기화
│   │   └── seed_data.py        # 개발용 시드 데이터
│   ├── models/                 # SQLAlchemy 모델
│   │   ├── user.py            # 사용자 모델
│   │   └── __init__.py
│   ├── schemas/                # Pydantic 스키마
│   │   ├── user.py            # 사용자 스키마
│   │   └── __init__.py
│   └── services/               # 비즈니스 로직
│       ├── auth_service.py    # 인증 서비스
│       └── s3_service.py      # S3 서비스
├── .github/workflows/
│   ├── ci.yml                  # 코드 품질 검사
│   └── cd.yml                  # ECS 배포 자동화
├── Dockerfile                  # Multi-stage Docker 빌드
├── docker-compose.yml          # 로컬 개발 환경
├── requirements.txt            # Python 의존성
└── init-db.sql                # 수동 DB 초기화 (백업용)
```

## 주요 구현 특징

### 1. 자동 데이터베이스 초기화
- 애플리케이션 시작 시 자동으로 테이블 생성
- 개발용 테스트 사용자 및 데이터 자동 생성
- 로컬과 프로덕션 환경 자동 구분

### 2. JWT 보안 인증 시스템
- Access Token (15분) + Refresh Token (30일) 구조
- HttpOnly 쿠키를 통한 Refresh Token 저장
- 자동 토큰 갱신 및 XSS/CSRF 공격 방지

### 3. S3 Presigned URL 방식
- 안전한 직접 파일 업로드
- 서버 부하 최소화
- 파일 타입 및 크기 제한

### 4. ML 서버 비동기 통신
- aiohttp 클라이언트 기반 비동기 처리
- Job 기반 백그라운드 처리
- 실시간 진행 상황 추적

### 5. 완전 자동화된 CI/CD
- GitHub Actions 기반 자동 배포
- 코드 품질 검사 (Ruff, Black, MyPy, Bandit)
- ECS Rolling 배포 및 안정성 확인

## 작업 히스토리

### 2025년 9월 9일

```
[13:00] 프로젝트 초기 설정 및 FastAPI 기본 구조 구성
- FastAPI 애플리케이션 생성
- 기본 라우터 및 헬스 체크 엔드포인트 구현
- SQLAlchemy 설정 및 데이터베이스 연결

[13:30] JWT 기반 인증 시스템 구현
- 사용자 모델 및 스키마 정의
- 회원가입/로그인 API 구현
- JWT 토큰 생성 및 검증 로직

[14:00] Google OAuth 2.0 통합
- Authlib를 이용한 OAuth 클라이언트 설정
- Google 로그인 시작 및 콜백 처리
- OAuth 사용자와 로컬 사용자 구분 관리

[14:30] S3 파일 업로드 시스템 구현
- Presigned URL 생성 API
- 파일 다운로드 URL 생성 API
- S3 서비스 클래스 구현

[15:00] ML 서버 통신 인터페이스 개발
- 비디오 분석 요청 API
- Job 상태 조회 API
- aiohttp 기반 비동기 통신

[15:30] 자동 데이터베이스 초기화 시스템
- 앱 시작시 자동 테이블 생성
- 개발용 시드 데이터 생성
- 환경별 조건부 실행

[16:00] Docker 컨테이너화
- Multi-stage Dockerfile 작성
- 프로덕션 최적화된 이미지 빌드
- docker-compose.yml 로컬 개발 환경

[16:30] CI/CD 파이프라인 구축
- GitHub Actions CI 워크플로우 (코드 품질 검사)
- GitHub Actions CD 워크플로우 (ECS 자동 배포)
- 환경변수 관리 시스템

[17:00] ECS 배포 환경 구성
- ECS Fargate 클러스터 설정
- ECR 이미지 저장소 연동
- 로드 밸런서 및 타겟 그룹 설정

[17:30] 첫 배포 및 문제 해결
- SECRET_KEY 환경변수 누락 문제 해결
- Task Definition 이름 오류 수정
- 의존성 문제 (aiohttp) 해결

[18:00] 배포 안정성 개선
- Docker 빌드 최적화
- CORS 설정 문제 해결
- 코드 품질 검사 오류 수정

[18:30] 데이터베이스 연결 준비
- RDS PostgreSQL 인스턴스 확인
- 데이터베이스 환경변수 설정
- 연결 테스트 준비

[20:30] JWT 보안 시스템 개선
- HttpOnly Cookie 방식으로 인증 시스템 재설계
- Access Token (15분) + Refresh Token (30일) 구조
- XSS/CSRF 공격 방지 보안 강화

[21:00] Refresh Token 시스템 구현
- 토큰 쌍 생성 및 검증 로직
- 토큰 타입별 구분 처리
- 자동 토큰 갱신 메커니즘

[21:30] 인증 API 보안 강화
- 모든 인증 엔드포인트 쿠키 방식으로 변경
- OAuth 콜백 보안 개선
- 로그아웃 시 쿠키 삭제 처리

[22:00] 토큰 관리 API 구현
- /refresh 엔드포인트 구현
- /logout 엔드포인트 구현
- 쿠키 기반 토큰 관리 시스템

[22:30] 프론트엔드 연동 준비
- AuthStore 메모리 기반으로 변경
- 자동 토큰 갱신 인터셉터 구현
- API 요청 시 쿠키 포함 설정

[23:00] 통합 인증 시스템 완성
- OAuth 콜백 처리 로직 개선
- 401 에러 시 자동 토큰 갱신
- 완전한 보안 인증 시스템 구축

[23:30] 프로젝트 문서화
- 전체 프로젝트 개요 문서 작성
- API 명세서 정리
- 작업 히스토리 및 기술 스택 정리
```

## 배포 환경

### AWS 인프라
- **ECS Fargate**: 컨테이너 실행 환경 (2개 태스크)
- **ECR**: Docker 이미지 저장소
- **S3**: 비디오 파일 저장
- **RDS PostgreSQL**: 사용자 데이터 저장
- **CloudFront**: CDN 및 프론트엔드 배포

### 환경변수 관리
- **GitHub Secrets**: 민감한 정보 보안 관리
- **ECS Task Definition**: 런타임 환경변수 주입
- **로컬 개발**: .env 파일 기반 설정

### CI/CD 파이프라인
1. **코드 커밋** → GitHub Repository
2. **CI 실행** → Ruff, Black, MyPy, Bandit 검사
3. **CD 실행** → Docker 이미지 빌드 및 ECR 푸시
4. **ECS 배포** → Task Definition 업데이트 및 서비스 재시작
5. **배포 검증** → 헬스 체크 및 안정성 확인

## 보안 특징

### 인증 보안
- JWT Access Token을 메모리에만 저장 (XSS 방지)
- Refresh Token을 HttpOnly 쿠키로 저장 (JavaScript 접근 차단)
- SameSite=lax 설정으로 CSRF 공격 방지
- 자동 토큰 갱신으로 사용자 경험 개선

### API 보안
- 모든 민감한 엔드포인트에 JWT 인증 필수
- Presigned URL을 통한 안전한 파일 업로드
- CORS 설정으로 도메인 접근 제한
- 입력 데이터 검증 및 SQL 인젝션 방지

### 인프라 보안
- HTTPS 강제 사용
- ECS 보안 그룹을 통한 네트워크 접근 제어
- 환경변수 암호화 저장
- 정기적인 보안 검사 (Bandit)

## 향후 개선 계획

### 기능 개선
- 사용자 이메일 인증 시스템
- 사용자 프로필 관리 기능
- 파일 업로드 진행률 표시
- ML 분석 결과 캐싱

### 성능 최적화
- 데이터베이스 인덱스 최적화
- Redis 기반 세션 관리
- CDN 캐싱 전략 개선
- API 응답 시간 모니터링

### 확장성 개선
- 마이크로서비스 아키텍처 전환
- 메시지 큐 도입 (SQS/RabbitMQ)
- 오토 스케일링 정책 개선
- 멀티 리전 배포

---
*최종 업데이트: 2025년 9월 9일*
*프로젝트: ECG Backend v1.0.0*