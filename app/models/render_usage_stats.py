"""
렌더링 사용량 통계 모델
"""

from sqlalchemy import Column, String, Date, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class RenderUsageStats(Base):
    """일별 렌더링 사용량 통계"""

    __tablename__ = "render_usage_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # 렌더링 카운트
    render_count = Column(Integer, default=0)
    render_success_count = Column(Integer, default=0)
    render_failed_count = Column(Integer, default=0)
    render_cancelled_count = Column(Integer, default=0)

    # 시간 통계 (초 단위)
    total_duration = Column(Float, default=0.0)  # 총 비디오 시간
    total_processing_time = Column(Float, default=0.0)  # 총 처리 시간
    avg_processing_time = Column(Float, default=0.0)  # 평균 처리 시간

    # 파일 크기 통계 (바이트)
    total_file_size = Column(Integer, default=0)
    avg_file_size = Column(Float, default=0.0)

    # 품질 통계
    total_cues_processed = Column(Integer, default=0)
    avg_cues_per_job = Column(Float, default=0.0)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 사용자별 일별 고유 제약
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "user_id": self.user_id,
            "date": self.date.isoformat(),
            "render_count": self.render_count,
            "success_rate": (
                self.render_success_count / self.render_count
                if self.render_count > 0
                else 0
            ),
            "avg_processing_time": self.avg_processing_time,
            "total_duration": self.total_duration,
            "avg_file_size": self.avg_file_size,
            "avg_cues_per_job": self.avg_cues_per_job,
        }


class RenderMonthlyStats(Base):
    """월별 렌더링 사용량 통계"""

    __tablename__ = "render_monthly_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    # 월별 집계 데이터
    render_count = Column(Integer, default=0)
    render_success_count = Column(Integer, default=0)
    render_failed_count = Column(Integer, default=0)

    total_duration = Column(Float, default=0.0)
    total_processing_time = Column(Float, default=0.0)
    avg_processing_time = Column(Float, default=0.0)

    total_file_size = Column(Integer, default=0)
    total_cues_processed = Column(Integer, default=0)

    # 요금 계산용 (향후 확장)
    estimated_cost = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 사용자별 월별 고유 제약
    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="uq_user_year_month"),
    )
