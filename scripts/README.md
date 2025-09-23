# S3 플러그인 업로드 스크립트

motiontext-renderer의 플러그인 파일들을 S3에 업로드하는 스크립트입니다.

## 사전 준비

### 1. 환경변수 설정

`.env` 파일에 다음 항목들이 설정되어 있어야 합니다:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-plugin-bucket-name
```

### 2. AWS 권한

사용하는 AWS 계정에 다음 권한이 필요합니다:
- `s3:CreateBucket` (버킷 생성)
- `s3:PutObject` (파일 업로드)
- `s3:PutBucketCors` (CORS 설정)
- `s3:HeadBucket` (버킷 존재 확인)

## 실행 방법

### 1. 스크립트 실행 권한 부여
```bash
chmod +x scripts/upload_plugins_to_s3.py
```

### 2. 스크립트 실행
```bash
cd /Users/yerin/Desktop/ecg-backend
python scripts/upload_plugins_to_s3.py
```

## 동작 과정

1. **버킷 확인/생성**: 지정된 S3 버킷이 없으면 자동 생성
2. **CORS 설정**: 프론트엔드 도메인에서 접근 가능하도록 CORS 정책 설정
3. **파일 업로드**: motiontext-renderer의 플러그인 파일들을 다음 구조로 업로드:
   ```
   s3://your-bucket/plugins/
   ├── rotation@2.0.0/
   │   ├── manifest.json
   │   └── index.mjs
   ├── fadein@2.0.0/
   │   ├── manifest.json
   │   └── index.mjs
   └── ...
   ```

## 업로드되는 파일들

소스: `/Users/yerin/Desktop/motiontext-renderer/demo/plugin-server/plugins/`

각 플러그인 디렉토리에서:
- `manifest.json` → `plugins/{plugin_name}/manifest.json`
- `index.mjs` → `plugins/{plugin_name}/index.mjs`

## 문제 해결

### AWS 자격 증명 오류
```
❌ AWS credentials not found in environment variables
```
→ `.env` 파일에 AWS 키가 올바르게 설정되었는지 확인

### 버킷 이름 오류
```
❌ S3_BUCKET_NAME 환경변수가 설정되지 않았습니다.
```
→ `.env` 파일에 `S3_BUCKET_NAME` 추가

### 권한 오류
```
❌ Access Denied
```
→ AWS IAM 사용자에게 S3 권한이 있는지 확인