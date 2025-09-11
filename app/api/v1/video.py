from fastapi import APIRouter, HTTPException

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
        except Exception:
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


