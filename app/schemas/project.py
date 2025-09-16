from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProjectSettings(BaseModel):
    """프로젝트 설정"""

    auto_save_enabled: bool = True
    auto_save_interval: int = 60  # 초 단위
    default_speaker: str = "Speaker"
    export_format: str = "srt"  # srt, vtt, ass


class VideoMetadata(BaseModel):
    """비디오 메타데이터"""

    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None


class WordSchema(BaseModel):
    """단어 스키마"""

    id: str
    text: str
    start: float
    end: float
    is_editable: bool = True
    confidence: Optional[float] = None
    applied_assets: Optional[List[str]] = None


class ClipItemSchema(BaseModel):
    """클립 아이템 스키마"""

    id: str
    timeline: str
    speaker: str
    subtitle: str
    full_text: str
    duration: str
    thumbnail: Optional[str] = None
    words: List[WordSchema] = []


class ProjectBase(BaseModel):
    """프로젝트 기본 스키마"""

    name: str
    settings: Optional[ProjectSettings] = None
    video_url: Optional[str] = None
    video_name: Optional[str] = None
    video_type: Optional[str] = None
    video_duration: Optional[float] = None
    video_metadata: Optional[VideoMetadata] = None


class ProjectCreate(ProjectBase):
    """프로젝트 생성 스키마"""

    id: str
    clips: List[ClipItemSchema] = []
    media_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    """프로젝트 업데이트 스키마"""

    name: Optional[str] = None
    clips: Optional[List[ClipItemSchema]] = None
    settings: Optional[ProjectSettings] = None
    video_url: Optional[str] = None
    video_name: Optional[str] = None
    video_type: Optional[str] = None
    video_duration: Optional[float] = None
    video_metadata: Optional[VideoMetadata] = None
    change_count: Optional[int] = None


class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마"""

    id: str
    clips: List[ClipItemSchema]
    created_at: datetime
    updated_at: datetime
    server_synced_at: Optional[datetime] = None
    sync_status: str = "pending"
    version: int = 1
    change_count: int = 0

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답 스키마"""

    id: str
    name: str
    last_modified: datetime
    size: Optional[int] = None  # bytes
    clip_count: int = 0
    video_duration: Optional[float] = None
    sync_status: str = "pending"

    class Config:
        from_attributes = True


class ProjectSyncResponse(BaseModel):
    """프로젝트 동기화 응답"""

    success: bool
    synced_at: datetime
    version: int


class ConflictResponse(BaseModel):
    """충돌 응답"""

    error: str = "CONFLICT"
    current_version: int
    your_version: int
    server_data: Optional[Dict[str, Any]] = None
    conflict_resolution: str = "merge"  # merge, overwrite, manual
