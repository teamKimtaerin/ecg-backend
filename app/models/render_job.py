"""
GPU 렌더링 작업 모델
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class RenderStatus(str, enum.Enum):
    """렌더링 작업 상태"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderJob(Base):
    """GPU 렌더링 작업 모델"""

    __tablename__ = "render_jobs"

    # Primary key
    job_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Status fields
    status = Column(String(20), nullable=False, default=RenderStatus.QUEUED)
    progress = Column(Integer, default=0)

    # Input data
    video_url = Column(Text, nullable=False)
    scenario = Column(JSONB, nullable=False)  # MotionText scenario
    options = Column(JSONB, nullable=True)  # Render options (width, height, fps, etc.)

    # Output data
    download_url = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)

    # Metadata
    estimated_time = Column(Integer, nullable=True)  # Estimated time in seconds
    estimated_time_remaining = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # User tracking (optional, for history)
    user_id = Column(String(255), nullable=True)
    video_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        # Index for status queries
        {"schema": None},
    )

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "jobId": str(self.job_id),
            "status": self.status,
            "progress": self.progress,
            "videoUrl": self.video_url,
            "downloadUrl": self.download_url,
            "estimatedTime": self.estimated_time,
            "estimatedTimeRemaining": self.estimated_time_remaining,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error_message,
            "errorCode": self.error_code,
        }
