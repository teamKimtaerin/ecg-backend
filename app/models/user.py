from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class AuthProvider(str, enum.Enum):
    """인증 제공자 타입"""

    LOCAL = "local"
    GOOGLE = "google"


class User(Base):
    """사용자 모델"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # OAuth 사용자는 null 가능

    # OAuth 관련 필드
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL)
    oauth_id = Column(String(255), nullable=True)  # Google OAuth ID 저장용

    # 계정 상태
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # 렌더링 할당량 설정
    # render_quota_daily = Column(Integer, default=10)  # 일일 렌더링 제한
    # render_quota_monthly = Column(Integer, default=100)  # 월간 렌더링 제한
    # concurrent_render_limit = Column(Integer, default=2)  # 동시 렌더링 제한

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
