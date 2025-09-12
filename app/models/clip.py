from sqlalchemy import Column, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Clip(Base):
    """자막 클립 모델 - 개별 자막 세그먼트 정보"""

    __tablename__ = "clips"

    # 기본 정보
    id = Column(String(255), primary_key=True, index=True)
    project_id = Column(
        String(255),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 클립 정보
    timeline = Column(String(50), nullable=True)  # "0:00:15" 형식
    speaker = Column(String(100), nullable=True)
    subtitle = Column(Text, nullable=True)  # 자막 미리보기 텍스트
    full_text = Column(Text, nullable=True)  # 전체 자막 텍스트

    # 타이밍 정보
    start_time = Column(Float, nullable=False)  # 초 단위
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)

    # 미디어 정보
    thumbnail_url = Column(Text, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # 관계
    project = relationship("Project", back_populates="clips_relation")
    words = relationship("Word", back_populates="clip", cascade="all, delete-orphan")
