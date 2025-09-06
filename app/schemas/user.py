from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """회원가입 요청 스키마"""

    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "securepassword123",
            }
        }


class UserLogin(BaseModel):
    """로그인 요청 스키마"""

    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")

    class Config:
        json_schema_extra = {
            "example": {"email": "john@example.com", "password": "securepassword123"}
        }


class UserResponse(BaseModel):
    """사용자 응답 스키마"""

    id: int
    username: str
    email: str
    auth_provider: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy 모델과 호환


class Token(BaseModel):
    """JWT 토큰 응답 스키마"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """토큰 페이로드 데이터"""

    user_id: Optional[int] = None
    email: Optional[str] = None
