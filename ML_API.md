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
    "filetype": "video/mp4"
  }
  ```

- **Response**:

  ```json
  {
    "url": "https://s3.amazonaws.com/...",
    "fileKey": "videos/anonymous/20250911_143020_abc12345_example.mp4"
  }
  ```

---

### 1-2. 영상 처리 요청

- **Endpoint**: `POST /api/upload-video/request-process`
- **Request Body**:

  ```json
  {
    "fileKey": "videos/anonymous/20250911_143020_abc12345_example.mp4"
  }
  ```

- **Response**:

  ```json
  {
    "message": "Video processing started.",
    "jobId": "123456"
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
