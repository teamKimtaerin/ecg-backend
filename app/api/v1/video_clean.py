from fastapi import APIRouter, HTTPException
import uuid
from app.services.s3_service import s3_service

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

    try:
        # 서비스 레이어 사용
        presigned_url, file_key = s3_service.generate_presigned_url(
            filename=filename,
            filetype=filetype,
            user_id=None  # 익명 사용자
        )
        
        print(f"[S3] Generated presigned URL for: {filename}")
        print(f"[S3] File key: {file_key}")
        
        return {
            "url": presigned_url,
            "fileKey": file_key
        }
        
    except Exception as e:
        print(f"[S3 ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


@router.get("/download-url/{file_key:path}")
async def generate_download_url(file_key: str):
    """
    파일 다운로드용 presigned URL 생성
    """
    try:
        download_url = s3_service.generate_download_url(file_key)
        
        print(f"[S3] Generated download URL for: {file_key}")
        
        return {
            "downloadUrl": download_url,
            "fileKey": file_key,
            "expiresIn": s3_service.presigned_expire
        }
        
    except Exception as e:
        if "File not found" in str(e):
            raise HTTPException(status_code=404, detail="File not found")
        print(f"[S3 DOWNLOAD ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


@router.post("/request-process")
async def request_process(request: dict):
    """
    비디오 처리 요청 (시연용)
    """
    file_key = request.get("fileKey")
    
    if not file_key:
        raise HTTPException(status_code=400, detail="fileKey is required")
    
    job_id = str(uuid.uuid4())
    print(f"[DEMO] Processing started for fileKey: {file_key}, jobId: {job_id}")
    
    return {
        "message": "Video processing started.",
        "jobId": job_id
    }


@router.post("/results")
async def receive_results(request: dict):
    """
    모델 서버 결과 수신 (시연용)
    """
    job_id = request.get("jobId")
    status = request.get("status")
    
    if not job_id or not status:
        raise HTTPException(status_code=400, detail="Invalid result data")
    
    print(f"[DEMO] Results received for jobId: {job_id}, status: {status}")
    
    return {
        "message": "Result received and saved."
    }


@router.get("/mock-result/{job_id}")
async def get_mock_result(job_id: str):
    """
    시연용 JSON 파일 결과 반환
    """
    import json
    from pathlib import Path
    
    json_file_path = Path("app/data/mock_result.json")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            mock_data = json.load(f)
        
        return {
            "jobId": job_id,
            "status": "success",
            **mock_data
        }
        
    except FileNotFoundError:
        return {
            "jobId": job_id,
            "status": "error",
            "message": "Mock data file not found"
        }
    except json.JSONDecodeError:
        return {
            "jobId": job_id,
            "status": "error", 
            "message": "Invalid JSON format"
        }