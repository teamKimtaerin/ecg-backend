from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class JobStatus(str, enum.Enum):
    """작업 상태 타입"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """작업 모델"""

    __tablename__ = "jobs"

    job_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    status = Column(String(20), nullable=False, default=JobStatus.PENDING)
    progress = Column(Integer, default=0)
    video_url = Column(Text, nullable=True)
    file_key = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
