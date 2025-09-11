## 📌 디렉토리 구조

프론트엔드 : /Users/yerin/Desktop/ecg-frontend

백엔드 : /Users/yerin/Desktop/ecg-backend

ML : /Users/yerin/Desktop/ecg-audio-analyzer/

---

## 📌 참고사항

---

## 📌 서비스 플로우 (큰 그림)

1. **클라이언트 → 백엔드**
   - S3 업로드 presigned URL 요청
   - presigned URL 받아서 직접 S3에 영상 업로드
2. **클라이언트 → 백엔드**
   - 업로드 완료 후, 처리 요청 (`/api/upload-video/request-process`)
3. **백엔드 → ML 서버**
   - 분석 요청 (`/api/upload-video/process-video`) 전달
4. **ML 서버**
   - Whisper 모델 실행 + 영상 분석
   - 진행 상황 상태값 관리 (폴링으로 확인 가능)
5. **클라이언트 → ML 서버 상태 확인**
   - 진행 상황 폴링 (`/api/upload-video/status/{job_id}`)
6. **ML 서버 → 백엔드**
   - 분석 완료 시, 결과 JSON을 백엔드로 전달
7. **백엔드 → 클라이언트**
   - 결과 확인 가능

---

## 📌 API 명세

### 1. **백엔드 (ECS FastAPI 서버)**

### 1-1. Presigned URL 생성

- **Endpoint**: `POST /api/upload-video/generate-url`
- **Request Body**:

  ```json
  {
    "filename": "example.mp4",
    "content_type": "video/mp4"
  }
  ```

- **Response**:

  ```json
  {
    "upload_url": "https://s3.amazonaws.com/...",
    "video_url": "https://bucket-name.s3.amazonaws.com/example.mp4"
  }
  ```

---

### 1-2. 영상 처리 요청

- **Endpoint**: `POST /api/upload-video/request-process`
- **Request Body**:

  ```json
  {
    "video_url": "https://bucket-name.s3.amazonaws.com/example.mp4"
  }
  ```

- **Response**:

  ```json
  {
    "job_id": "123456",
    "status": "processing"
  }
  ```

➡️ 이 요청을 받은 백엔드는 **ML 서버에 `/process-video` 호출**

---

### 1-3. ML 서버 결과 수신 (ML 서버 → 백엔드 콜백)

- **Endpoint**: `POST /api/upload-video/result`
- **Request Body** (ML 서버가 Whisper 결과 그대로 전송):

  ```json
  {
    "job_id": "123456",
    "result": {
      "text": "Hello world",
      "segments": [
        { "start": 0.0, "end": 2.3, "text": "Hello" },
        { "start": 2.4, "end": 4.0, "text": "world" }
      ],
      "language": "en"
    }
  }
  ```

- **Response**:

  ```json
  {
    "status": "received"
  }
  ```

---

### 2. **ML 서버 (EC2, Whisper 실행 서버)**

### 2-1. 영상 분석 요청

- **Endpoint**: `POST /api/upload-video/process-video`
- **Request Body**:

  ```json
  {
    "job_id": "123456",
    "video_url": "https://bucket-name.s3.amazonaws.com/example.mp4"
  }
  ```

- **Response**:

  ```json
  {
    "job_id": "123456",
    "status": "processing"
  }
  ```

---

### 2-2. 상태 확인 (클라이언트 폴링용)

- **Endpoint**: `GET /api/upload-video/status/{job_id}`
- **Response (처리 중)**:

  ```json
  {
    "job_id": "123456",
    "status": "processing",
    "progress": 40
  }
  ```

- **Response (완료 시)**:

  ```json
  {
    "job_id": "123456",
    "status": "completed"
  }
  ```

---

### 2-3. 결과 백엔드로 전송

- **Endpoint (백엔드 콜백 호출)**: `POST /api/upload-video/result`
- **Body**: Whisper의 원본 JSON 그대로 전달

  ```json
  {
    "job_id": "123456",
    "result": { ... }
  }
  ```

---

## 📌 전체 플로우 테스트 가이드

### 🔄 **완전한 테스트 플로우**

다음 단계를 순서대로 실행하여 S3 업로드부터 ML 분석 완료까지 전체 파이프라인을 테스트할 수 있습니다.

### **1단계: S3 Presigned URL 생성**

```bash
curl -X POST "http://ecg-project-pipeline-dev-alb-1703405864.us-east-1.elb.amazonaws.com/api/upload-video/generate-url" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "sample.mp4",
    "filetype": "video/mp4"
  }'
```

**응답 예시**:
```json
{
  "url": "https://ecg-project-pipeline-dev-video-storage-np9digv7.s3.amazonaws.com/videos/anonymous/20250911_034548_3b3673a3_sample.mp4?AWSAccessKeyId=...",
  "fileKey": "videos/anonymous/20250911_034548_3b3673a3_sample.mp4"
}
```

### **2단계: S3에 실제 파일 업로드**

```bash
# 1단계에서 받은 presigned URL 사용
curl -X PUT "https://ecg-project-pipeline-dev-video-storage-np9digv7.s3.amazonaws.com/videos/anonymous/20250911_034548_3b3673a3_sample.mp4?AWSAccessKeyId=..." \
  -H "Content-Type: video/mp4" \
  --data-binary @"/Users/yerin/Desktop/ecg-frontend/sample.mp4"
```

### **3단계: ML 처리 요청**

```bash
# Job ID 생성 및 ML 처리 요청
JOB_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Generated Job ID: $JOB_ID"

curl -X POST "http://ecg-project-pipeline-dev-alb-1703405864.us-east-1.elb.amazonaws.com/api/upload-video/process-video" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"$JOB_ID\",
    \"video_url\": \"https://ecg-project-pipeline-dev-video-storage-np9digv7.s3.amazonaws.com/videos/anonymous/20250911_034548_3b3673a3_sample.mp4\"
  }"
```

**응답 예시**:
```json
{
  "job_id": "b276b1c2-5b50-40fa-ac7a-9cdef2781f5d",
  "status": "processing",
  "message": "비디오 처리가 시작되었습니다",
  "status_url": "/api/upload-video/status/b276b1c2-5b50-40fa-ac7a-9cdef2781f5d"
}
```

### **4단계: 상태 폴링**

```bash
# 단일 상태 확인
curl "http://ecg-project-pipeline-dev-alb-1703405864.us-east-1.elb.amazonaws.com/api/upload-video/status/$JOB_ID"

# 연속 상태 폴링 (5회, 3초 간격)
for i in {1..5}; do
  echo "[$i] $(date): Checking status..."
  curl -s "http://ecg-project-pipeline-dev-alb-1703405864.us-east-1.elb.amazonaws.com/api/upload-video/status/$JOB_ID" | jq .
  echo ""
  sleep 3
done
```

**응답 예시 (처리 중)**:
```json
{
  "job_id": "b276b1c2-5b50-40fa-ac7a-9cdef2781f5d",
  "status": "processing",
  "progress": 0
}
```

**응답 예시 (완료)**:
```json
{
  "job_id": "b276b1c2-5b50-40fa-ac7a-9cdef2781f5d",
  "status": "completed"
}
```

### **5단계: 모든 작업 목록 확인 (디버깅용)**

```bash
curl "http://ecg-project-pipeline-dev-alb-1703405864.us-east-1.elb.amazonaws.com/api/upload-video/jobs"
```

---

## 🔧 **트러블슈팅**

### **문제 1: "해당 작업을 찾을 수 없습니다"**
- **원인**: ML 서버와의 통신 실패, 백그라운드 작업 예외 발생
- **확인**: 모든 작업 목록이 비어있는지 확인
- **해결**: EC2 ML 서버 상태 및 네트워크 연결 확인

### **문제 2: 상태가 "processing"에서 변경되지 않음**
- **원인**: ML 서버에서 결과 콜백이 오지 않음
- **해결**: ML 서버 로그 확인, 콜백 URL 설정 확인

### **디버깅 명령어**

```bash
# EC2 ML 서버 직접 상태 확인 (EC2 내부에서 실행)
curl -X GET "http://localhost:8080/health"

# ECS에서 EC2로 직접 연결 테스트
curl -X GET "http://[EC2_PRIVATE_IP]:8080/health"
```
