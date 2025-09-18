"""
YouTube 할당량 관리 DB 모델
"""

from sqlalchemy import Column, Integer, Date, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class YouTubeQuotaUsage(Base):
    """YouTube API 할당량 사용량 추적 테이블"""

    __tablename__ = "youtube_quota_usage"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)  # 날짜별 유니크
    used_quota = Column(Integer, default=0, nullable=False)  # 사용된 할당량
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<YouTubeQuotaUsage(date={self.date}, used_quota={self.used_quota})>"