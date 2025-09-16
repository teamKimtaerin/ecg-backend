# ML Server URL Update

## 변경 내용
- **이전 ML Server URL**: `http://localhost:8080` (로컬 개발용)
- **새로운 ML Server URL**: `http://54.237.160.54:8080` (EC2 인스턴스)

## 테스트 결과
✅ **연결 테스트 성공**
```json
{
  "status": "processing",
  "job_id": "test-connection-123",
  "message": "Processing started successfully"
}
```

## 환경별 설정

### 로컬 개발 환경 (.env)
```bash
MODEL_SERVER_URL=http://54.237.160.54:8080
```

### Fargate 배포 환경 (GitHub Secrets)
**업데이트 필요한 Secret:**
- `MODEL_SERVER_URL`: `http://54.237.160.54:8080`

## API 엔드포인트
- **ML 서버**: `POST http://54.237.160.54:8080/api/upload-video/process-video`
- **콜백 URL**: `POST {fastapi_base_url}/api/upload-video/result`

## 배포 준비 상태
- ✅ 로컬 환경 테스트 완료
- ✅ ML 서버 연결 확인
- ✅ API 코드 검증 완료
- ⏳ GitHub Secrets 업데이트 필요

## 다음 단계
1. GitHub Secrets에서 `MODEL_SERVER_URL` 업데이트
2. main 브랜치로 병합하여 Fargate 배포 트리거
3. CloudFront URL에서 배포 확인

---
생성일: 2025-09-17
업데이트: ML Server를 EC2 인스턴스로 이전