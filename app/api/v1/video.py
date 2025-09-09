from fastapi import APIRouter, HTTPException
import uuid
import time

router = APIRouter(prefix="/api/upload-video", tags=["video"])


@router.post("/generate-url")
async def generate_presigned_url(request: dict):
    """
    실제 S3 사전 서명된 URL 발급
    """
    filename = request.get("filename")
    filetype = request.get("filetype")

    if not filename or not filetype:
        raise HTTPException(status_code=400, detail="Invalid filename or filetype")

    # ========== MOCK 코드 (주석 처리) ==========
    # fake_file_key = f"videos/demo/{int(time.time())}_{filename}"
    # fake_presigned_url = f"https://demo-bucket.s3.ap-northeast-2.amazonaws.com/{fake_file_key}?X-Amz-Algorithm=AWS4-HMAC-SHA256&expires=3600"
    # return {"url": fake_presigned_url, "fileKey": fake_file_key}

    # ========== 실제 S3 연동 코드 ==========
    try:
        import boto3
        import uuid
        from datetime import datetime
        import os

        # 환경변수에서 AWS 설정 읽기
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        presigned_expire = int(os.getenv("S3_PRESIGNED_URL_EXPIRE", "3600"))

        if not all([aws_access_key_id, aws_secret_access_key, s3_bucket_name]):
            raise Exception(
                "Missing AWS credentials or bucket name in environment variables"
            )

        # S3 클라이언트 생성
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

        # 파일 키 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_key = f"videos/anonymous/{timestamp}_{unique_id}_{filename}"

        # presigned URL 생성
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": s3_bucket_name, "Key": file_key, "ContentType": filetype},
            ExpiresIn=presigned_expire,
        )

        print(f"[S3 TEST] Generated presigned URL for: {filename}")
        print(f"[S3 TEST] File key: {file_key}")
        print(f"[S3 TEST] Bucket: {s3_bucket_name}")
        print(f"[S3 TEST] URL: {presigned_url}")

        return {"url": presigned_url, "fileKey": file_key}

    except Exception as e:
        print(f"[S3 ERROR] Failed to generate presigned URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


@router.get("/download-url/{file_key:path}")
async def generate_download_url(file_key: str):
    """
    파일 다운로드용 presigned URL 생성
    """
    try:
        import boto3
        import os

        # 환경변수에서 AWS 설정 읽기
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        presigned_expire = int(os.getenv("S3_PRESIGNED_URL_EXPIRE", "3600"))

        if not all([aws_access_key_id, aws_secret_access_key, s3_bucket_name]):
            raise Exception(
                "Missing AWS credentials or bucket name in environment variables"
            )

        # S3 클라이언트 생성
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

        # 파일 존재 확인
        try:
            s3_client.head_object(Bucket=s3_bucket_name, Key=file_key)
        except:
            raise HTTPException(status_code=404, detail="File not found")

        # 다운로드용 presigned URL 생성
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket_name, "Key": file_key},
            ExpiresIn=presigned_expire,
        )

        print(f"[S3 DOWNLOAD] Generated download URL for: {file_key}")
        print(f"[S3 DOWNLOAD] URL: {download_url}")

        return {
            "downloadUrl": download_url,
            "fileKey": file_key,
            "expiresIn": presigned_expire,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[S3 DOWNLOAD ERROR] Failed to generate download URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


# 시연용 job 상태 저장소 (실제로는 DB 사용)
job_storage = {}


@router.post("/request-process")
async def request_process(request: dict):
    """
    실제 ML 서버로 비디오 처리 요청
    """
    file_key = request.get("fileKey")

    if not file_key:
        raise HTTPException(status_code=400, detail="fileKey is required")

    # ML 서버 호출
    try:
        import httpx
        import os
        import asyncio
        
        model_server_url = os.getenv("MODEL_SERVER_URL", "http://10.0.10.42:8080")
        
        print(f"[ML SERVER] Calling ML server: {model_server_url}/request-process?video_key={file_key}")
        
        # ML 서버로 비동기 요청
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{model_server_url}/request-process",
                params={"video_key": file_key}
            )
            
            if response.status_code == 200:
                ml_result = response.json()
                ml_job_id = ml_result.get("job_id")
                
                # Backend job ID와 ML job ID 매핑 저장
                backend_job_id = str(uuid.uuid4())
                job_storage[backend_job_id] = {
                    "jobId": backend_job_id,
                    "mlJobId": ml_job_id,
                    "fileKey": file_key,
                    "status": "processing",
                    "message": "Video processing in progress on ML server...",
                    "progress": 0,
                    "createdAt": time.time(),
                    "result": None,
                }
                
                print(f"[ML SERVER] Success - Backend Job ID: {backend_job_id}, ML Job ID: {ml_job_id}")
                return {"message": "Video processing started.", "jobId": backend_job_id}
            else:
                print(f"[ML SERVER ERROR] Status: {response.status_code}, Response: {response.text}")
                raise HTTPException(status_code=500, detail=f"ML server error: {response.status_code}")
                
    except Exception as e:
        print(f"[ML SERVER ERROR] Failed to call ML server: {str(e)}")
        
        # ML 서버 호출 실패시 폴백 모드
        job_id = str(uuid.uuid4())
        job_storage[job_id] = {
            "jobId": job_id,
            "fileKey": file_key,
            "status": "processing",
            "message": "Processing with fallback mode (ML server unavailable)...",
            "progress": 0,
            "createdAt": time.time(),
            "result": None,
        }
        
        # 폴백으로 시뮬레이션 실행
        asyncio.create_task(simulate_processing(job_id))
        
        return {"message": "Video processing started (fallback mode).", "jobId": job_id}


async def simulate_processing(job_id: str):
    """시연용: 처리 시뮬레이션"""
    import asyncio

    # 2초 후 50% 진행
    await asyncio.sleep(2)
    if job_id in job_storage:
        job_storage[job_id].update(
            {
                "status": "processing",
                "progress": 50,
                "message": "Extracting audio and analyzing emotions...",
            }
        )

    # 3초 더 후 완료
    await asyncio.sleep(3)
    if job_id in job_storage:
        job_storage[job_id].update(
            {
                "status": "completed",
                "progress": 100,
                "message": "Processing completed successfully!",
                "result": "mock_result_available",
            }
        )
        print(f"[DEMO] Job {job_id} completed")


@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Job 상태 조회 API
    """
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = job_storage[job_id].copy()

    # 완료된 job이면 mock_result.json 데이터 포함
    if job_info["status"] == "completed" and job_info["result"]:
        try:
            import json
            from pathlib import Path

            json_file_path = Path("app/data/mock_result.json")
            with open(json_file_path, "r", encoding="utf-8") as f:
                mock_data = json.load(f)

            job_info["transcriptionResult"] = mock_data

        except Exception as e:
            print(f"[ERROR] Failed to load mock result: {e}")
            job_info["transcriptionResult"] = {"error": "Failed to load result data"}

    return job_info


@router.post("/results")
async def receive_results(request: dict):
    """
    시연용: 모델 서버에서 결과 수신
    mock_result.json 내용 포함하여 응답
    """
    job_id = request.get("jobId")
    status = request.get("status")

    if not job_id or not status:
        raise HTTPException(status_code=400, detail="Invalid result data")

    print(f"[DEMO] Results received for jobId: {job_id}, status: {status}")

    # mock_result.json 내용 로드하여 반환
    try:
        import json
        from pathlib import Path

        json_file_path = Path("app/data/mock_result.json")
        with open(json_file_path, "r", encoding="utf-8") as f:
            mock_data = json.load(f)

        return {
            "message": "Result received and saved.",
            "jobId": job_id,
            "status": status,
            **mock_data,  # mock_result.json 내용 포함
        }

    except Exception as e:
        print(f"[ERROR] Failed to load mock result: {e}")
        return {
            "message": "Result received and saved.",
            "jobId": job_id,
            "status": status,
            "error": "Failed to load result data",
        }


@router.get("/mock-result/{job_id}")
async def get_mock_result(job_id: str):
    """
    시연용: JSON 파일에서 결과 반환
    """
    import json
    from pathlib import Path

    # JSON 파일 경로 설정
    json_file_path = Path("app/data/mock_result.json")

    try:
        # JSON 파일 읽기
        with open(json_file_path, "r", encoding="utf-8") as f:
            mock_data = json.load(f)

        # job_id를 응답에 포함
        response = {
            "jobId": job_id,
            "status": "success",
            **mock_data,  # JSON 파일의 모든 내용 포함
        }

        return response

    except FileNotFoundError:
        return {
            "jobId": job_id,
            "status": "error",
            "message": "Mock data file not found. Please add mock_result.json to app/data/ folder",
        }
    except json.JSONDecodeError:
        return {
            "jobId": job_id,
            "status": "error",
            "message": "Invalid JSON format in mock data file",
        }
