from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WordBase(BaseModel):
    """단어 기본 스키마"""

    text: str
    start: float
    end: float
    confidence: Optional[float] = None
    is_editable: bool = True
    applied_assets: Optional[List[str]] = None


class WordCreate(WordBase):
    """단어 생성 스키마"""

    id: str


class WordResponse(WordBase):
    """단어 응답 스키마"""

    id: str
    clip_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClipBase(BaseModel):
    """클립 기본 스키마"""

    timeline: Optional[str] = None
    speaker: Optional[str] = None
    subtitle: Optional[str] = None
    full_text: Optional[str] = None
    start_time: float
    end_time: float
    duration: float
    thumbnail_url: Optional[str] = None


class ClipCreate(ClipBase):
    """클립 생성 스키마"""

    id: str
    words: Optional[List[WordCreate]] = []


class ClipUpdate(BaseModel):
    """클립 업데이트 스키마"""

    timeline: Optional[str] = None
    speaker: Optional[str] = None
    subtitle: Optional[str] = None
    full_text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    words: Optional[List[WordCreate]] = None


class ClipResponse(ClipBase):
    """클립 응답 스키마"""

    id: str
    project_id: str
    words: List[WordResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClipBulkUpdate(BaseModel):
    """클립 일괄 업데이트 스키마"""

    added: List[ClipCreate] = []
    modified: List[ClipUpdate] = []
    deleted: List[str] = []  # 삭제할 클립 ID 목록
