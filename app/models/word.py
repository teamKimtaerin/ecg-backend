from sqlalchemy import Column, String, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Word(Base):
    """단어 모델 - 클립 내 개별 단어 정보"""

    __tablename__ = "words"

    # 기본 정보
    id = Column(String(255), primary_key=True, index=True)
    clip_id = Column(
        String(255),
        ForeignKey("clips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 단어 정보
    text = Column(String(255), nullable=False)

    # 타이밍 정보 (초 단위)
    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)

    # 추가 정보
    confidence = Column(Float, nullable=True)  # 0.0 ~ 1.0
    is_editable = Column(Boolean, default=True)
    applied_assets = Column(JSON, nullable=True)  # 적용된 애니메이션 효과 등

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    clip = relationship("Clip", back_populates="words")
