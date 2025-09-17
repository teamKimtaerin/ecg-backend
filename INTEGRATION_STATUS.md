# ECG Project Integration Status

## Last Updated: 2025-09-17

## ✅ Completed Integration Tasks

### 1. Language Selection Feature
- **Frontend**: Language selector implemented in `NewUploadModal.tsx`
  - Options: Korean (ko), English (en), Japanese (ja), Chinese (zh)
  - Default: Korean (ko)
  - Location: `/src/components/NewUploadModal.tsx:40`

- **API Service**: Language parameter passed in upload service
  - File: `/src/services/api/uploadService.ts:214-218`
  - Sends language as optional parameter to backend

- **Backend API**: Language parameter received and forwarded
  - Endpoint: `POST /api/upload-video/request-process`
  - File: `/app/api/v1/ml_video.py:179`
  - Default: "auto" if not provided

- **ML Server Communication**: Language sent to ML server
  - File: `/app/api/v1/ml_video.py:492`
  - Payload includes language for WhisperX optimization (30% performance improvement)

### 2. Environment Configuration Updates
- **Backend** (`.env`):
  ```env
  MODEL_SERVER_URL=http://10.0.10.42:8001  # Private network ML server
  FASTAPI_BASE_URL=https://ho-it.site      # CloudFront distribution
  CORS_ORIGINS=http://localhost:3000,https://d31nzc58rhgh3i.cloudfront.net,https://ho-it.site
  ```

- **Frontend Production** (`.env`):
  ```env
  NEXT_PUBLIC_API_URL=https://ho-it.site
  ```

- **Frontend Local** (`.env.local`):
  ```env
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

### 3. API Documentation
- Created comprehensive `FRONTEND_API_GUIDE.md` with:
  - Complete API endpoint documentation
  - TypeScript interfaces for type safety
  - React implementation examples
  - Request/response models with examples
  - Error handling strategies
  - Auto-save with conflict resolution

## ⏳ Pending Tasks

### 1. CloudFront /api/* Routing Issue
- **Problem**: `https://ho-it.site/api/*` returns S3 response instead of routing to ALB
- **Status**: Infrastructure team confirmed configuration but routing not working
- **Workaround**: Currently using direct ALB URL until CloudFront is fixed
- **Test URL**: `https://ho-it.site/api/health` (should return {"status":"healthy"})

### 2. Fargate Service Deployment
- **Required**: Redeploy ECS Fargate service with updated environment variables
- **Changes**: New `FASTAPI_BASE_URL` and `CORS_ORIGINS` values
- **Command**: `aws ecs update-service --force-new-deployment`

### 3. ML Server Callback Validation
- **Verify**: ML server sends correct callback structure to `/api/upload-video/result`
- **Expected Fields**: job_id, status, progress, result (with segments array)
- **Documentation**: Aligned with ML server API integration guide

## 🔄 Current Data Flow

```
1. Upload Flow:
   Frontend (localhost:3000)
   → CloudFront (ho-it.site)
   → ALB (ecg-alb-*.elb.amazonaws.com)
   → Fargate Backend (:8000)
   → ML Server (10.0.10.42:8001)

2. Language Selection:
   User selects language in UI
   → Passed via uploadService.requestMLProcessing(file_key, language)
   → Backend receives in ClientProcessRequest
   → Forwards to ML server in trigger_ml_server payload
   → WhisperX uses language hint for 30% better performance

3. Callback Flow:
   ML Server processes video
   → POST to FASTAPI_BASE_URL/api/upload-video/result
   → Backend updates job status in PostgreSQL
   → Frontend polls /api/upload-video/status/{job_id}
   → Results displayed in editor
```

## 📝 Configuration Files

### Backend
- `/app/core/config.py` - Environment variable management
- `/app/api/v1/ml_video.py` - ML server integration endpoints
- `/app/api/v1/auth.py` - Authentication with Google OAuth
- `.env` - Environment variables (not in git)

### Frontend
- `/src/config/api.config.ts` - API endpoint configuration
- `/src/lib/api/auth.ts` - Authentication service
- `/src/services/api/uploadService.ts` - Video upload service
- `/src/components/NewUploadModal.tsx` - Upload UI with language selection
- `.env` / `.env.local` - Environment variables

## 🐛 Known Issues

1. **CloudFront Routing**: /api/* paths not forwarding to ALB origin
2. **Git Conflicts**: Resolved with merge strategy `git pull --no-rebase origin main`
3. **Language Parameter**: Initially removed, then re-added as optional for performance

## 📊 Testing Checklist

- [ ] Frontend can reach backend through CloudFront (waiting for fix)
- [x] Language selection UI working in NewUploadModal
- [x] Language parameter passed to backend API
- [x] Backend forwards language to ML server
- [ ] ML server processes with correct language hint
- [ ] Callback from ML server received successfully
- [ ] Results displayed in frontend editor

## 🚀 Next Steps

1. Monitor CloudFront fix from infrastructure team
2. Deploy updated Fargate service with new env vars
3. End-to-end testing with real video upload
4. Performance testing with different language selections
5. Monitor WhisperX performance improvements with language hints

## 📞 Contact Points

- **Backend**: FastAPI on ECS Fargate
- **ML Server**: EC2 instance at 10.0.10.42:8001
- **Frontend**: Next.js on CloudFront + S3
- **Database**: PostgreSQL RDS instance