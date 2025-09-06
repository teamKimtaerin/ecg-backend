from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
import httpx
from app.models.user import User, AuthProvider
from app.schemas.user import UserCreate
from app.core.config import settings
import os

# 비밀번호 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간


class AuthService:
    """인증 관련 서비스"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해시화"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        return user
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """새 사용자 생성"""
        # 비밀번호 해시화
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        # 사용자 생성
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """사용자명으로 사용자 조회"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_oauth_id(db: Session, oauth_id: str, provider: AuthProvider) -> Optional[User]:
        """OAuth ID로 사용자 조회"""
        return db.query(User).filter(
            User.oauth_id == oauth_id, 
            User.auth_provider == provider
        ).first()
    
    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        """Google OAuth 토큰으로 사용자 정보 가져오기"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    def create_oauth_user(
        db: Session, 
        email: str, 
        username: str, 
        oauth_id: str, 
        provider: AuthProvider
    ) -> User:
        """OAuth 사용자 생성"""
        db_user = User(
            username=username,
            email=email,
            password_hash=None,  # OAuth 사용자는 비밀번호 없음
            auth_provider=provider,
            oauth_id=oauth_id,
            is_verified=True  # OAuth 사용자는 이미 인증됨
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user


# OAuth 클라이언트 설정
oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# 싱글톤 인스턴스
auth_service = AuthService()