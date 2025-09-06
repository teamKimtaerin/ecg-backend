from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from authlib.integrations.base_client.errors import OAuthError
from app.db.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import auth_service, oauth
from app.models.user import User, AuthProvider
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


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
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 이메일입니다."
        )

    # 사용자명 중복 확인
    if auth_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 사용자명입니다."
        )

    # 사용자 생성
    try:
        user = auth_service.create_user(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}",
        )

    # JWT 토큰 생성
    access_token = auth_service.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user),
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
            status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다. 관리자에게 문의하세요."
        )

    # JWT 토큰 생성
    access_token = auth_service.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user),
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    현재 로그인한 사용자 정보 조회
    - JWT 토큰으로 사용자 확인
    """
    # 토큰 검증
    payload = auth_service.verify_token(credentials.credentials)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )

    return UserResponse.from_orm(user)


@router.get("/google/login")
async def google_login(request: Request):
    """
    Google OAuth 로그인 시작
    - Google 로그인 페이지로 리디렉션
    """
    google = oauth.create_client("google")
    redirect_uri = settings.google_redirect_uri

    return await google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=Token)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth 콜백 처리
    - Google에서 돌아온 인증 정보로 사용자 로그인/회원가입 처리
    """
    try:
        google = oauth.create_client("google")
        token = await google.authorize_access_token(request)

        # Google 사용자 정보 가져오기
        user_info = await auth_service.get_google_user_info(token["access_token"])

        google_id = user_info["id"]
        email = user_info["email"]
        username = user_info.get("name", email.split("@")[0])

        # 기존 OAuth 사용자 확인
        user = auth_service.get_user_by_oauth_id(db, google_id, AuthProvider.GOOGLE)

        if not user:
            # 이메일로 기존 사용자 확인 (로컬 계정이 있는 경우)
            existing_user = auth_service.get_user_by_email(db, email)
            if existing_user and existing_user.auth_provider == AuthProvider.LOCAL:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미 '{email}' 계정으로 가입된 사용자가 있습니다. 일반 로그인을 사용해주세요.",
                )

            # 새 OAuth 사용자 생성
            user = auth_service.create_oauth_user(
                db=db,
                email=email,
                username=username,
                oauth_id=google_id,
                provider=AuthProvider.GOOGLE,
            )

        # JWT 토큰 생성
        access_token = auth_service.create_access_token(
            data={"user_id": user.id, "email": user.email}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user),
        }

    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth 인증 실패: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google 로그인 처리 중 오류가 발생했습니다: {str(e)}",
        )


# 헤더에서 토큰 추출하는 헬퍼 함수
async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Authorization 헤더에서 Bearer 토큰 추출"""
    return credentials.credentials
