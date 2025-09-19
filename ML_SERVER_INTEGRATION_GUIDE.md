# ML Server 통신 API 완전 가이드

## 📋 개요

이 문서는 ECG Backend와 ML 서버 간의 통신 아키텍처를 상세히 설명하는 완전한 가이드입니다. ML 서버는 비디오 파일을 분석하여 음성 전사, 화자 분리, 감정 분석 등을 수행하는 외부 WhisperX 기반 분석 서버입니다.

## 🏗️ 시스템 아키텍처

### 통신 플로우
```
[Frontend] → [ECG Backend] → [S3 Storage] → [ML Server] → [ECG Backend]
    ↑                                                           ↓
    └─────────────── 결과 폴링 ←──────────────────────────────────┘
```

### 주요 구성 요소
1. **ECG Backend (FastAPI)**: 주 백엔드 서버 (Port: 8000)
2. **ML Server**: WhisperX 기반 음성 분석 서버 (Port: 8080)
3. **AWS S3**: 비디오 파일 저장소
4. **PostgreSQL**: 작업 상태 및 결과 저장

### 처리 단계
1. **업로드**: 클라이언트가 S3 Presigned URL로 비디오 업로드
2. **요청**: ECG Backend가 ML 서버로 분석 요청 전송
3. **처리**: ML 서버가 비디오 다운로드 후 WhisperX로 분석
4. **콜백**: ML 서버가 결과를 ECG Backend로 콜백 전송
5. **폴링**: 클라이언트가 상태를 주기적으로 확인

## 🔧 관련 파일 구조

```
app/
├── api/v1/
│   ├── ml_video.py              # ML 서버 통신 엔드포인트
│   └── video.py                 # S3 Presigned URL 생성
├── services/
│   ├── s3_service.py            # S3 통신 서비스
│   └── job_service.py           # 작업 상태 관리
├── models/
│   └── job.py                   # 작업 모델 정의
├── core/
│   └── config.py                # 환경 변수 설정
└── db/
    └── database.py              # 데이터베이스 연결
```

## 🌍 환경 변수 설정

### ML 서버 관련 환경 변수

| 변수명 | 기본값 | 설명 | 파일 위치 |
|--------|--------|------|-----------|
| `MODEL_SERVER_URL` | - | ML 서버 기본 URL | app/core/config.py:37-39 |
| `ml_api_server_url` | http://54.237.160.54:8080 | ML API 서버 URL (호환성) | app/core/config.py:41-43 |
| `ML_API_TIMEOUT` | 300 | ML API 타임아웃 (초) | app/core/config.py:45-47 |
| `FASTAPI_BASE_URL` | http://localhost:8000 | 콜백을 위한 백엔드 URL | app/core/config.py:48-51 |

### S3 관련 환경 변수

| 변수명 | 기본값 | 설명 | 파일 위치 |
|--------|--------|------|-----------|
| `AWS_ACCESS_KEY_ID` | - | AWS 액세스 키 | app/core/config.py:26 |
| `AWS_SECRET_ACCESS_KEY` | - | AWS 시크릿 키 | app/core/config.py:27 |
| `AWS_REGION` | ap-northeast-2 | AWS 리전 | app/core/config.py:28 |
| `S3_BUCKET_NAME` | - | S3 버킷 이름 | app/core/config.py:31 |
| `S3_PRESIGNED_URL_EXPIRE` | 3600 | Presigned URL 만료 시간 (초) | app/core/config.py:32-34 |

### 환경 변수 설정 예시 (.env)
```bash
# ML 서버 설정
MODEL_SERVER_URL=http://ml-server:8080
ML_API_TIMEOUT=300
FASTAPI_BASE_URL=http://localhost:8000

# AWS S3 설정
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-northeast-2
S3_BUCKET_NAME=ecg-video-storage
S3_PRESIGNED_URL_EXPIRE=3600
```

## 📡 API 엔드포인트 상세

### 1. S3 Presigned URL 생성

#### 엔드포인트
```http
POST /api/upload-video/generate-url
```

#### 구현 위치
- **파일**: `app/api/v1/video.py:33-110`
- **함수**: `generate_presigned_url()`

#### 요청 구조
```json
{
  "filename": "video.mp4",
  "content_type": "video/mp4"
}
```

#### 응답 구조
```json
{
  "presigned_url": "https://bucket.s3.region.amazonaws.com/key?signed-params",
  "file_key": "videos/anonymous/20240101_120000_abc12345_video.mp4",
  "expires_in": 3600,
  "url": "...",         // 레거시 호환성
  "fileKey": "..."      // 레거시 호환성
}
```

#### S3 서비스 클래스
- **파일**: `app/services/s3_service.py`
- **클래스**: `S3Service`
- **주요 메서드**:
  - `generate_presigned_url()`: 업로드용 URL 생성 (42-63행)
  - `generate_download_url()`: 다운로드용 URL 생성 (64-83행)
  - `check_file_exists()`: 파일 존재 확인 (84-93행)

### 2. ML 서버 처리 요청

#### 엔드포인트
```http
POST /api/upload-video/request-process
```

#### 구현 위치
- **파일**: `app/api/v1/ml_video.py:173-232`
- **함수**: `request_process()`

#### 요청 구조
```json
{
  "fileKey": "videos/user/timestamp_unique_filename.mp4",
  "language": "auto"  // 선택적, 기본값: "auto"
}
```

#### 응답 구조
```json
{
  "message": "Video processing started.",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 내부 처리 흐름 (app/api/v1/ml_video.py:186-227)
1. **입력 검증** (188-189행): fileKey 필수 확인
2. **Job ID 생성** (192-194행): UUID4 형식으로 생성
3. **S3 URL 구성** (196-203행): 환경변수 기반 URL 생성
4. **DB 작업 생성** (205-213행): JobService로 상태 저장
5. **백그라운드 처리** (221행): ML 서버 요청을 비동기로 실행

### 3. ML 서버 콜백 수신

#### 엔드포인트
```http
POST /api/upload-video/result
```

#### 구현 위치
- **파일**: `app/api/v1/ml_video.py:238-478`
- **함수**: `receive_ml_results()`

#### ML 서버에서 보내는 요청 구조
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Processing completed",
  "result": {
    "metadata": {
      "filename": "video.mp4",
      "duration": 143.39,
      "total_segments": 25,
      "unique_speakers": 4
    },
    "segments": [
      {
        "start_time": 4.908,      // ML 서버 형식
        "end_time": 8.754,        // ML 서버 형식
        "speaker": {
          "speaker_id": "SPEAKER_01"
        },
        "text": "You know, we should all do. Go see a musical.",
        "words": [
          {
            "word": "You",
            "start": 4.908,
            "end": 4.988,
            "volume_db": -19.87,
            "pitch_hz": 851.09
          }
        ]
      }
    ]
  },
  "error_message": null,
  "error_code": null
}
```

#### 타임스탬프 필드 정규화 (app/api/v1/ml_video.py:48-89)
ML 서버와 백엔드 간 타임스탬프 필드명 차이를 해결:
- **ML 서버**: `start_time`, `end_time`
- **백엔드**: `start`, `end`
- **처리**: `normalize_timestamp_fields()` 함수로 자동 변환

#### HMAC 서명 검증 (app/api/v1/ml_video.py:32-46)
```python
def verify_hmac_signature(request_body: bytes, signature: str, secret_key: str) -> bool:
    expected_signature = hmac.new(
        secret_key.encode("utf-8"), request_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

### 4. 작업 상태 조회 (클라이언트 폴링용)

#### 엔드포인트
```http
GET /api/upload-video/status/{job_id}
```

#### 구현 위치
- **파일**: `app/api/v1/ml_video.py:480-521`
- **함수**: `get_job_status()`

#### 응답 구조
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "result": {
    // ML 분석 결과 데이터
  }
}
```

### 5. ML 서버 헬스체크

#### 엔드포인트
```http
GET /api/upload-video/ml-server/health
```

#### 구현 위치
- **파일**: `app/api/v1/ml_video.py:523-591`
- **함수**: `check_ml_server_health()`

#### 응답 구조
```json
{
  "status": "healthy",
  "ml_server_url": "http://ml-server:8080",
  "response_time_ms": 245.67,
  "http_status": 200,
  "response": "ML Server is running"
}
```

## 🔄 비동기 처리 워크플로우

### 백그라운드 태스크 함수들

#### 1. ML 서버 요청 전송 (app/api/v1/ml_video.py:598-620)
```python
async def trigger_ml_server(job_id: str, request: VideoProcessRequest, db_session=None):
    """EC2 ML 서버에 분석 요청을 전송하는 백그라운드 태스크"""
```

#### 2. ML 서버 통신 핵심 함수 (app/api/v1/ml_video.py:659-823)
```python
async def _send_request_to_ml_server(
    job_id: str,
    payload: Dict[str, Any],
    db_session=None,
    retry_count: int = 0,
    max_retries: int = 2,
) -> None:
```

#### ML 서버로 전송되는 페이로드 (app/api/v1/ml_video.py:675-680)
```json
{
  "job_id": "uuid",
  "video_url": "s3-presigned-url",
  "fastapi_base_url": "http://backend:8000",
  "language": "auto"
}
```

### 재시도 로직 (app/api/v1/ml_video.py:781-787)
```python
if retry_count < max_retries:
    wait_time = (retry_count + 1) * 5  # 5초, 10초, 15초 대기
    logger.info(f"🔄 {wait_time}초 후 재시도합니다... ({retry_count + 1}/{max_retries})")
    await asyncio.sleep(wait_time)
    return await _send_request_to_ml_server(
        job_id, payload, db_session, retry_count + 1, max_retries
    )
```

## 🗄️ 데이터베이스 모델

### Job 모델 (app/models/job.py)

#### 테이블 구조
```sql
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    video_url TEXT,
    file_key TEXT,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### JobStatus 열거형 (app/models/job.py:9-16)
```python
class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### JobService 클래스 (app/services/job_service.py)

#### 주요 메서드
```python
class JobService:
    def create_job(self, job_id, status, progress, video_url, file_key) -> Job
    def get_job(self, job_id: str) -> Optional[Job]
    def update_job_status(self, job_id, status, progress, result, error_message) -> bool
    def list_all_jobs(self, limit: int = 100) -> List[Job]
    def delete_job(self, job_id: str) -> bool
```

## 🔒 보안 기능

### 1. HMAC 서명 검증 (app/api/v1/ml_video.py:268-284)
```python
signature_header = request.headers.get("X-Signature-256", "")
webhook_secret = getattr(settings, "webhook_secret_key", None) or settings.secret_key

if signature_header and webhook_secret:
    if not verify_hmac_signature(request_body, signature_header, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
```

### 2. Rate Limiting (app/api/v1/ml_video.py:174)
```python
@limiter.limit("5/minute")
async def request_process():
```

### 3. 멱등성 보장 (app/api/v1/ml_video.py:387-403)
```python
if job.status == "completed" and ml_result.status in ["completed", "processing"]:
    logger.info(f"멱등성 처리 - 이미 완료된 작업에 대한 콜백")
    return MLResultResponse(status="already_completed")
```

### 4. S3 보안 설정
- **Presigned URL 만료**: 기본 1시간 (3600초)
- **읽기 전용 권한**: GET 요청만 허용
- **HTTPS 강제**: 모든 S3 요청은 HTTPS 사용

## 🚨 에러 처리

### 에러 상태 업데이트 (app/api/v1/ml_video.py:808-823)
```python
async def _update_job_status_error(db_session, job_id: str, error_message: str, error_code: str):
    job_service = JobService(db_session)
    job_service.update_job_status(
        job_id=job_id,
        status="failed",
        error_message=f"{error_code}: {error_message}",
    )
```

### 일반적인 에러 코드
- `TIMEOUT_ERROR`: ML 서버 처리 타임아웃
- `CONNECTION_ERROR`: ML 서버 연결 실패
- `UNKNOWN_ERROR`: 알 수 없는 오류
- `ML_SERVER_ERROR`: ML 서버 내부 오류

### 프론트엔드 오용 감지 (app/api/v1/ml_video.py:320-346)
```python
if user_agent == "node" or "status" in str(e.errors()[0].get("loc", [])):
    error_detail = {
        "error": "⚠️ Frontend API Misuse Detected - Wrong Endpoint!",
        "message": "🚨 이 엔드포인트는 ML 서버 전용입니다!",
        "correct_endpoint": "GET /api/upload-video/status/{job_id}",
        "wrong_endpoint": "POST /api/upload-video/result (ML Server Webhook Only)"
    }
```

## 🧪 테스트 및 디버깅

### 1. ML 서버 헬스체크
```bash
curl http://localhost:8000/api/upload-video/ml-server/health
```

### 2. Presigned URL 생성 테스트
```bash
curl -X POST http://localhost:8000/api/upload-video/generate-url \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.mp4", "content_type": "video/mp4"}'
```

### 3. 비디오 처리 요청 테스트
```bash
curl -X POST http://localhost:8000/api/upload-video/request-process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"fileKey": "videos/test/file.mp4", "language": "auto"}'
```

### 4. 작업 상태 확인
```bash
curl http://localhost:8000/api/upload-video/status/JOB_ID
```

### 로깅 설정
주요 로그 위치:
- **ML 서버 요청**: `app/api/v1/ml_video.py:602, 687, 724`
- **콜백 수신**: `app/api/v1/ml_video.py:291, 366`
- **에러 처리**: `app/api/v1/ml_video.py:760, 775, 798`

## ⚡ 성능 최적화

### 1. 타임아웃 설정
- **ML API 타임아웃**: 300초 (5분)
- **S3 Presigned URL**: 3600초 (1시간)
- **헬스체크 타임아웃**: 10초

### 2. 동시 처리 제한
- **Rate Limiting**: 5 requests/minute per IP
- **백그라운드 태스크**: 비동기 처리로 응답 시간 단축

### 3. 데이터베이스 최적화
- **인덱스**: job_id에 자동 인덱스
- **JSONB 타입**: 결과 데이터 효율적 저장
- **커넥션 풀링**: SQLAlchemy 기본 설정 사용

## 🔧 문제 해결

### 1. 연결 문제
```python
# ML 서버 연결 확인
async with aiohttp.ClientSession() as session:
    async with session.get(f"{ML_SERVER_URL}/health") as response:
        if response.status == 200:
            print("ML 서버 정상")
```

### 2. S3 권한 문제
```python
# S3 접근 권한 확인
try:
    s3_client.head_object(Bucket=bucket_name, Key=file_key)
    print("S3 파일 접근 가능")
except ClientError as e:
    print(f"S3 오류: {e}")
```

### 3. 콜백 누락 문제
- **네트워크 확인**: ML 서버에서 백엔드로 접근 가능한지 확인
- **URL 확인**: `FASTAPI_BASE_URL` 환경변수 정확성 확인
- **방화벽**: 포트 8000 접근 허용 확인

## 📊 모니터링 및 로깅

### 중요 로그 메시지
```python
# 성공적인 처리
logger.info(f"새 비디오 처리 요청 - Job ID: {job_id}")
logger.info(f"ML 서버에 요청 전송 완료 - Job ID: {job_id}")
logger.info(f"작업 완료 - Job ID: {job_id}")

# 에러 상황
logger.error(f"ML 서버 요청 실패 - Job ID: {job_id}, Error: {str(e)}")
logger.warning(f"존재하지 않는 Job ID: {job_id}")
```

### 메트릭 수집 지점
- **요청 수**: ML 서버로 전송된 총 요청 수
- **성공률**: 완료된 작업 대비 성공한 작업 비율
- **평균 처리 시간**: 요청부터 완료까지 소요 시간
- **에러율**: 실패한 작업의 비율

---

이 가이드를 통해 ECG Backend와 ML 서버 간의 통신을 완전히 이해하고 구현할 수 있습니다.