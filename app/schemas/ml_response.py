"""
ML 응답을 위한 간소화된 스키마들
프론트엔드 요구사항에 맞춰 최적화된 구조
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class SimplifiedWord(BaseModel):
    """간소화된 단어 정보"""

    word: str
    start: float
    end: float
    volume_db: float  # 애니메이션 강도용 (-60 ~ 0 범위)
    pitch_hz: float  # 애니메이션 선택용 (100 ~ 1000 범위)


class SimplifiedSegment(BaseModel):
    """간소화된 세그먼트 정보"""

    start_time: float
    end_time: float
    speaker_id: str
    text: str
    words: List[SimplifiedWord]


class SimplifiedMetadata(BaseModel):
    """간소화된 메타데이터"""

    filename: str
    duration: float
    total_segments: int
    unique_speakers: int


class SimplifiedTranscriptionResult(BaseModel):
    """간소화된 전사 결과"""

    jobId: str
    status: str  # "success" | "error"
    metadata: SimplifiedMetadata
    segments: List[SimplifiedSegment]


class JobStatusResponse(BaseModel):
    """작업 상태 응답 (프론트엔드 요구사항)"""

    status: str  # "queued" | "started" | "processing" | "completed" | "failed"
    progress: int  # 0-100 정수값
    current_message: Optional[str] = None
    message: Optional[str] = None
    error_message: Optional[str] = None
    results: Optional[SimplifiedTranscriptionResult] = None


class ErrorResponse(BaseModel):
    """표준 에러 응답"""

    success: bool = False
    error: Dict[str, Any]


class SuccessResponse(BaseModel):
    """표준 성공 응답"""

    success: bool = True
    data: Dict[str, Any]


def get_progress_message(progress: int) -> str:
    """진행률에 따른 메시지 반환"""
    if progress <= 10:
        return "Initializing processing..."
    elif progress <= 25:
        return "Extracting audio from video..."
    elif progress <= 40:
        return "Detecting speech segments..."
    elif progress <= 60:
        return "Identifying speakers..."
    elif progress <= 75:
        return "Generating transcription..."
    elif progress <= 90:
        return "Analyzing emotions and confidence..."
    else:
        return "Finalizing results..."


def create_error_response(
    code: str, message: str, details: Dict[str, Any] = None
) -> ErrorResponse:
    """표준 에러 응답 생성"""
    error_data = {"code": code, "message": message}
    if details:
        error_data["details"] = details

    return ErrorResponse(error=error_data)


def create_success_response(data: Dict[str, Any]) -> SuccessResponse:
    """표준 성공 응답 생성"""
    return SuccessResponse(data=data)


def simplify_ml_result(
    raw_result: Dict[str, Any], job_id: str
) -> SimplifiedTranscriptionResult:
    """
    복잡한 ML 결과를 프론트엔드 요구사항에 맞게 간소화

    Args:
        raw_result: ML 서버에서 받은 원본 결과
        job_id: 작업 ID

    Returns:
        SimplifiedTranscriptionResult: 간소화된 결과
    """

    # 메타데이터 추출 및 간소화
    metadata = SimplifiedMetadata(
        filename=raw_result.get("metadata", {}).get("filename", "unknown.mp4"),
        duration=raw_result.get("metadata", {}).get("duration", 0.0),
        total_segments=raw_result.get("metadata", {}).get("total_segments", 0),
        unique_speakers=raw_result.get("metadata", {}).get("unique_speakers", 0),
    )

    # 세그먼트 간소화
    simplified_segments = []
    raw_segments = raw_result.get("segments", [])

    for segment in raw_segments:
        # 단어 정보 추출 및 간소화
        simplified_words = []
        raw_words = segment.get("words", [])

        for word in raw_words:
            simplified_word = SimplifiedWord(
                word=word.get("word", ""),
                start=word.get("start", 0.0),
                end=word.get("end", 0.0),
                volume_db=word.get("volume_db", -30.0),  # 기본값
                pitch_hz=word.get("pitch_hz", 300.0),  # 기본값
            )
            simplified_words.append(simplified_word)

        # 세그먼트 정보 간소화
        simplified_segment = SimplifiedSegment(
            start_time=segment.get("start_time", 0.0),
            end_time=segment.get("end_time", 0.0),
            speaker_id=segment.get("speaker", {}).get("speaker_id", "UNKNOWN"),
            text=segment.get("text", ""),
            words=simplified_words,
        )
        simplified_segments.append(simplified_segment)

    return SimplifiedTranscriptionResult(
        jobId=job_id, status="success", metadata=metadata, segments=simplified_segments
    )
