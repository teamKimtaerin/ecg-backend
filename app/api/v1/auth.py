from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import auth_service
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    회원가입 API
    - username, email, password를 받아 새 사용자 생성
    - 생성 후 자동으로 로그인 토큰 발급
    """
    # 이메일 중복 확인
    if auth_service.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다."
        )
    
    # 사용자명 중복 확인
    if auth_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다."
        )
    
    # 사용자 생성
    try:
        user = auth_service.create_user(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}"
        )
    
    # JWT 토큰 생성
    access_token = auth_service.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    로그인 API
    - email과 password로 인증
    - 성공 시 JWT 토큰 발급
    """
    # 사용자 인증
    user = auth_service.authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 계정 활성화 상태 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요."
        )
    
    # JWT 토큰 생성
    access_token = auth_service.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자 정보 조회
    - JWT 토큰으로 사용자 확인
    """
    # 토큰 검증
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 조회
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return UserResponse.from_orm(user)


# 헤더에서 토큰 추출하는 헬퍼 함수
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_token_from_header(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Authorization 헤더에서 Bearer 토큰 추출"""
    return credentials.credentials