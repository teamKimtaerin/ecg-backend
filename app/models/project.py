from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Project(Base):
    """프로젝트 모델 - 자막 프로젝트 정보 저장"""

    __tablename__ = "projects"

    # 기본 정보
    id = Column(String(255), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # 프로젝트 데이터 (JSONB for PostgreSQL)
    clips = Column(JSON, default=list)  # ClipItem[] 저장
    settings = Column(JSON, default=dict)  # ProjectSettings 저장

    # 미디어 정보
    media_id = Column(String(255), nullable=True)
    video_url = Column(Text, nullable=True)
    video_name = Column(String(255), nullable=True)
    video_type = Column(String(50), nullable=True)
    video_duration = Column(Float, nullable=True)
    video_metadata = Column(JSON, nullable=True)

    # 동기화 정보
    version = Column(Integer, default=1)
    change_count = Column(Integer, default=0)
    server_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(
        String(20), default="pending"
    )  # pending, syncing, synced, failed

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # 관계
    user = relationship("User", backref="projects")
    clips_relation = relationship(
        "Clip", back_populates="project", cascade="all, delete-orphan"
    )
