# ML 서버 API 명세서

## 📋 개요

이 문서는 ECG Backend와 ML 서버 간의 통신 규격을 정의합니다. ML 서버는 비디오 파일을 분석하여 음성 전사, 화자 분리, 감정 분석 등을 수행하는 외부 서버입니다.

## 🔗 통신 아키텍처

```
[Frontend localhost:3000] → [ECG Backend localhost:8000] → [ML Server localhost:8080]
     ↑            ↑              ↓
     └─────── Callback ←─────────┘
```

1. **Frontend** → ECG Backend: 비디오 처리 요청
2. **ECG Backend** → ML Server: 비동기 처리 요청
3. **ML Server** → ECG Backend: 처리 완료 후 콜백

## 🚀 ML 서버 요청 API

### 1. 비디오 처리 요청

#### Endpoint
```http
POST {ML_SERVER_URL}/api/upload-video/process-video
```

#### Headers
```http
Content-Type: application/json
User-Agent: ECS-FastAPI-Backend/1.0
```

#### Request Body
```json
{
  "job_id": "string",        // 고유 작업 ID (UUID 형식)
  "video_url": "string"      // S3 presigned URL (다운로드용)
}
```

#### Request 예시
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "video_url": "https://ecg-bucket.s3.amazonaws.com/videos/user/video.mp4?AWSAccessKeyId=..."
}
```

#### Success Response (200 OK)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Processing started",
  "estimated_time": 300
}
```

#### Error Response (400/500)
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "video_url is required",
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 2. 환경 변수 설정

ML 서버 URL은 다음 환경변수로 설정:
```bash
# Primary URL (권장)
MODEL_SERVER_URL=http://ml-server:8080

# Alternative URL (호환성)
ml_api_server_url=http://ml-server:8080
```

## 📡 ML 서버 콜백 API (ECG Backend 제공)

### 1. 처리 진행률 업데이트

#### Endpoint
```http
POST {BACKEND_URL}/api/v1/ml/ml-results
```

#### Headers
```http
Content-Type: application/json
User-Agent: ML-Server/1.0
```

#### Progress Update Request Body
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 65,
  "message": "Analyzing speech segments..."
}
```

### 2. 처리 완료 결과 전송

#### Success Result Request Body
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "result": {
    "metadata": {
      "filename": "video.mp4",
      "duration": 143.39,
      "total_segments": 25,
      "unique_speakers": 4
    },
    "segments": [
      {
        "start_time": 4.908,
        "end_time": 8.754,
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
          },
          {
            "word": "know",
            "start": 5.0,
            "end": 5.2,
            "volume_db": -22.1,
            "pitch_hz": 420.5
          }
        ]
      }
    ]
  }
}
```

### 3. 처리 실패 결과 전송

#### Error Result Request Body
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": 45,
  "error_message": "Audio extraction failed: unsupported codec",
  "error_code": "AUDIO_EXTRACTION_ERROR"
}
```

## 📊 데이터 구조 상세 명세

### 1. Metadata 구조
```json
{
  "metadata": {
    "filename": "string",        // 원본 파일명
    "duration": "number",        // 총 길이 (초)
    "total_segments": "number",  // 총 세그먼트 수
    "unique_speakers": "number"  // 고유 화자 수
  }
}
```

### 2. Segment 구조
```json
{
  "start_time": "number",      // 세그먼트 시작 시간 (초)
  "end_time": "number",        // 세그먼트 종료 시간 (초)
  "speaker": {
    "speaker_id": "string"     // 화자 ID (예: "SPEAKER_01")
  },
  "text": "string",               // 전사된 텍스트
  "words": [/* Word 배열 */]   // 단어별 상세 정보
}
```

### 3. Word 구조 (필수 필드만)
```json
{
  "word": "string",           // 단어
  "start": "number",          // 단어 시작 시간 (초)
  "end": "number",            // 단어 종료 시간 (초)
  "volume_db": "number",      // 음량 (dB, -60~0 범위)
  "pitch_hz": "number"        // 피치 (Hz, 100~1000 범위)
}
```

## ⚡ Status 및 Progress 가이드

### Status 값
- `"accepted"`: 요청 접수됨
- `"processing"`: 처리 중
- `"completed"`: 성공적으로 완료
- `"failed"`: 처리 실패

### Progress 단계 (0-100)
ML 서버에서 다음과 같은 단계로 progress를 업데이트하면 프론트엔드에서 적절한 메시지를 표시합니다:

- `0-10%`: 초기화 단계
- `10-25%`: 오디오 추출
- `25-40%`: 음성 구간 감지
- `40-60%`: 화자 식별
- `60-75%`: 전사 생성
- `75-90%`: 감정 및 신뢰도 분석
- `90-100%`: 결과 정리

## 🔧 ML 서버 구현 가이드

### 1. 처리 플로우
```python
# 1. 요청 받기
@app.post("/api/upload-video/process-video")
async def process_video(request):
    job_id = request.job_id
    video_url = request.video_url

    # 2. 백그라운드 작업 시작
    background_tasks.add_task(process_video_task, job_id, video_url)

    return {"job_id": job_id, "status": "accepted"}

# 3. 백그라운드 처리
async def process_video_task(job_id, video_url):
    try:
        # Progress 업데이트
        await send_progress(job_id, 10, "processing")

        # 비디오 다운로드
        video_file = download_video(video_url)
        await send_progress(job_id, 25, "processing")

        # 오디오 추출
        audio_file = extract_audio(video_file)
        await send_progress(job_id, 40, "processing")

        # 음성 인식
        segments = transcribe_audio(audio_file)
        await send_progress(job_id, 75, "processing")

        # 결과 전송
        await send_results(job_id, segments)

    except Exception as e:
        await send_error(job_id, str(e))
```

### 2. 콜백 전송 함수
```python
async def send_progress(job_id, progress, status):
    payload = {
        "job_id": job_id,
        "status": status,
        "progress": progress
    }

    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{BACKEND_URL}/api/v1/ml/ml-results",
            json=payload
        )

async def send_results(job_id, result_data):
    payload = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "result": result_data
    }

    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{BACKEND_URL}/api/v1/ml/ml-results",
            json=payload
        )
```

## 🚨 에러 처리

### ML 서버에서 Backend로 에러 보고
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": 30,
  "error_message": "Failed to download video from S3",
  "error_code": "DOWNLOAD_ERROR"
}
```

### 일반적인 에러 코드
- `DOWNLOAD_ERROR`: 비디오 다운로드 실패
- `AUDIO_EXTRACTION_ERROR`: 오디오 추출 실패
- `TRANSCRIPTION_ERROR`: 음성 인식 실패
- `PROCESSING_TIMEOUT`: 처리 시간 초과
- `INSUFFICIENT_RESOURCES`: 리소스 부족

## 📝 테스트 케이스

### 1. 성공 시나리오 테스트
```bash
# 1. ML 서버에 처리 요청
curl -X POST http://ml-server:8080/api/upload-video/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "video_url": "https://test-bucket.s3.amazonaws.com/test.mp4"
  }'

# 2. Backend에서 progress 확인
curl http://backend:8000/api/v1/ml/job-status/test-123
```

### 2. 에러 시나리오 테스트
```bash
# 잘못된 video_url로 테스트
curl -X POST http://ml-server:8080/api/upload-video/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-error",
    "video_url": "https://invalid-url.com/nonexistent.mp4"
  }'
```

## 🔒 보안 고려사항

### 1. S3 Presigned URL 보안
- URL 만료 시간: 1시간 (3600초)
- 읽기 전용 권한만 부여
- HTTPS 강제 사용

### 2. 콜백 보안
- Backend URL 화이트리스트 설정
- 요청 크기 제한 (최대 50MB)
- Rate limiting 적용

### 3. 에러 정보 보안
- 시스템 내부 경로 노출 금지
- 스택 트레이스 제외
- 일반화된 에러 메시지 사용

## 📊 성능 요구사항

### 1. 응답 시간
- 초기 요청 응답: < 5초
- Progress 업데이트: 30초마다
- 최대 처리 시간: 30분

### 2. 리소스 제한
- 최대 동시 처리: 10개 작업
- 최대 비디오 길이: 60분
- 최대 파일 크기: 2GB

## 📞 문제 해결

### 1. 연결 문제
- ML 서버 health check: `GET /health`
- 네트워크 연결 확인
- 방화벽 설정 점검

### 2. 처리 지연
- 서버 리소스 모니터링
- 큐 상태 확인
- 로그 분석

### 3. 결과 누락
- 콜백 URL 확인
- 네트워크 재시도 로직
- 수동 상태 조회

---

**이 명세서를 기반으로 ML 서버를 구현하시면 ECG Backend와 완벽하게 연동됩니다.**
