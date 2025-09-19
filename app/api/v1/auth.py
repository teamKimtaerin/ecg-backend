from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from authlib.integrations.base_client.errors import OAuthError
from app.db.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import auth_service, oauth
from app.models.user import User, AuthProvider
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
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

    # 사용자 생성
    try:
        user = auth_service.create_user(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 생성 중 오류가 발생했습니다: {str(e)}",
        )

    # JWT 토큰 쌍 생성
    access_token, refresh_token = auth_service.create_token_pair(
        data={"user_id": user.id, "email": user.email}
    )

    # Response 생성
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        }
    )

    # 쿠키 설정 결정: 크로스 도메인 환경에서는 도메인 설정하지 않음
    is_production = bool(settings.domain)
    # 크로스 도메인 환경에서는 쿠키 도메인을 설정하지 않음 (SameSite=None 사용)
    cookie_domain = None

    # Access token을 HttpOnly 쿠키로 설정 (세션 유지용)
    response.set_cookie(
        key="access_token",
        value=access_token,
        domain=cookie_domain,
        httponly=True,
        secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
        samesite="none" if is_production else "lax",
        max_age=24 * 60 * 60,  # 24시간
    )

    # Refresh token을 HttpOnly 쿠키로 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        domain=cookie_domain,
        httponly=True,
        secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
        samesite="none" if is_production else "lax",
        max_age=30 * 24 * 60 * 60,  # 30일
    )

    return response


@router.post("/login")
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

    # JWT 토큰 쌍 생성
    access_token, refresh_token = auth_service.create_token_pair(
        data={"user_id": user.id, "email": user.email}
    )

    # Response 생성
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        }
    )

    # 쿠키 설정 결정: 크로스 도메인 환경에서는 도메인 설정하지 않음
    is_production = bool(settings.domain)
    # 크로스 도메인 환경에서는 쿠키 도메인을 설정하지 않음 (SameSite=None 사용)
    cookie_domain = None

    # Access token을 HttpOnly 쿠키로 설정 (세션 유지용)
    response.set_cookie(
        key="access_token",
        value=access_token,
        domain=cookie_domain,
        httponly=True,
        secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
        samesite="none" if is_production else "lax",
        max_age=24 * 60 * 60,  # 24시간
    )

    # Refresh token을 HttpOnly 쿠키로 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        domain=cookie_domain,
        httponly=True,
        secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
        samesite="none" if is_production else "lax",
        max_age=30 * 24 * 60 * 60,  # 30일
    )

    return response


async def get_current_user_dependency(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    현재 로그인한 사용자를 반환하는 의존성 함수
    - JWT 토큰 (Bearer 헤더 또는 HttpOnly 쿠키)으로 사용자 확인
    - Origin 헤더 검증으로 CSRF 공격 방지
    """
    # CSRF 보호: Origin 검증 (쿠키 기반 인증 시)
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    # 허용된 origin 목록
    allowed_origins = [
        "https://ho-it.site",
        "http://localhost:3000",  # 개발 환경
    ]

    token = None

    # 1. Authorization 헤더에서 토큰 확인 (우선순위, Origin 검증 불필요)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # "Bearer " 제거

    # 2. HttpOnly 쿠키에서 access_token 확인 (Origin 검증 필요)
    if not token:
        # CSRF 보호: 쿠키 기반 인증 시 Origin 검증
        if origin not in allowed_origins and not any(referer and referer.startswith(ao) for ao in allowed_origins):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="요청 출처가 허용되지 않습니다.",
            )
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_dependency),
):
    """
    현재 로그인한 사용자 정보 조회
    - JWT 토큰 (Bearer 또는 HttpOnly 쿠키)으로 사용자 확인
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Refresh token을 이용해 새로운 access token 발급
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token이 없습니다.",
        )

    # Refresh token 검증
    payload = auth_service.verify_token(
        refresh_token, token_type="refresh"
    )  # nosec B106
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 refresh token입니다.",
        )

    # 사용자 조회
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다."
        )

    # 새로운 access token 생성
    new_access_token = auth_service.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    # Response 생성
    response = JSONResponse(
        content={
            "access_token": new_access_token,
            "token_type": "bearer",
        }
    )

    # 쿠키 설정 결정: 크로스 도메인 환경에서는 도메인 설정하지 않음
    is_production = bool(settings.domain)
    # 크로스 도메인 환경에서는 쿠키 도메인을 설정하지 않음 (SameSite=None 사용)
    cookie_domain = None

    # 새로운 Access token을 HttpOnly 쿠키로 업데이트 (세션 유지용)
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        domain=cookie_domain,
        httponly=True,
        secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
        samesite="none" if is_production else "lax",
        max_age=24 * 60 * 60,  # 24시간
    )

    return response


@router.post("/logout")
async def logout():
    """
    로그아웃 - refresh token 쿠키 삭제
    """
    response = JSONResponse(content={"message": "로그아웃 되었습니다."})

    # 쿠키 삭제 시 도메인 설정 (크로스 도메인 환경에서는 None)
    cookie_domain = None

    response.delete_cookie(key="refresh_token", domain=cookie_domain)
    response.delete_cookie(key="access_token", domain=cookie_domain)
    return response


@router.get("/google/login")
async def google_login(request: Request):
    """
    Google OAuth 로그인 시작
    - Google 로그인 페이지로 리디렉션
    - CloudFront 프록시 환경에서의 올바른 redirect_uri 처리
    """
    google = oauth.create_client("google")
    redirect_uri = settings.google_redirect_uri

    # CloudFront 환경 디버깅 정보
    current_host = request.headers.get("host", "")
    via_header = request.headers.get("via", "")

    print(f"OAuth login initiated from host: {current_host}")
    print(f"Via header: {via_header}")
    print(f"Configured redirect_uri: {redirect_uri}")

    # 세션 상태 확인 및 로깅
    session_before = dict(request.session) if request.session else {}
    print(f"Session before OAuth redirect: {session_before}")

    response = await google.authorize_redirect(request, redirect_uri)

    # 세션 상태 변화 확인
    session_after = dict(request.session) if request.session else {}
    print(f"Session after OAuth redirect: {session_after}")

    return response


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth 콜백 처리
    - Google에서 돌아온 인증 정보로 사용자 로그인/회원가입 처리
    - 성공 시 프론트엔드로 토큰과 함께 리디렉션
    - CloudFront 프록시 환경에서의 세션 상태 처리 개선
    """
    try:
        # 디버깅을 위한 로그 추가
        print(f"OAuth callback received: {request.url}")

        # CloudFront 프록시 환경에서의 세션 정보 확인
        session_data = request.session
        print(f"Session data available: {bool(session_data)}")
        print(f"Session keys: {list(session_data.keys()) if session_data else 'None'}")

        google = oauth.create_client("google")

        # CloudFront 환경에서 올바른 redirect_uri 확인
        original_redirect_uri = settings.google_redirect_uri
        current_host = request.headers.get("host", "")

        # CloudFront 도메인인 경우 실제 설정된 URI로 대체
        if "cloudfront.net" in current_host and "ho-it.site" in original_redirect_uri:
            print(
                f"CloudFront callback detected. Using configured redirect_uri: {original_redirect_uri}"
            )

        token = await google.authorize_access_token(request)

        print(f"Token received: {bool(token)}")

        # Google 사용자 정보 가져오기
        user_info = await auth_service.get_google_user_info(token["access_token"])

        # 디버깅: 구글에서 받은 사용자 정보 확인
        print(f"Google user_info received: {user_info}")

        google_id = user_info["id"]
        email = user_info["email"]
        username = user_info.get("name", email.split("@")[0])

        # 디버깅: 추출된 사용자 정보 확인
        print(f"Extracted - google_id: {google_id}, email: {email}, username: {username}")

        # 기존 OAuth 사용자 확인
        user = auth_service.get_user_by_oauth_id(db, google_id, AuthProvider.GOOGLE)

        if user:
            # 디버깅: 기존 사용자 로그인
            print(f"Existing OAuth user found - id: {user.id}, username: {user.username}, email: {user.email}")

        if not user:
            # 이메일로 기존 사용자 확인 (로컬 계정이 있는 경우)
            existing_user = auth_service.get_user_by_email(db, email)
            if existing_user and existing_user.auth_provider == AuthProvider.LOCAL:
                # 에러 상황에서도 프론트엔드로 리디렉션
                error_message = f"이미 '{email}' 계정으로 가입된 사용자가 있습니다. 일반 로그인을 사용해주세요."
                return RedirectResponse(
                    url=f"{settings.frontend_url}/auth/callback?error={error_message}"
                )

            # 새 OAuth 사용자 생성
            user = auth_service.create_oauth_user(
                db=db,
                email=email,
                username=username,
                oauth_id=google_id,
                provider=AuthProvider.GOOGLE,
            )
            # 디버깅: 생성된 사용자 정보 확인
            print(f"Created OAuth user - id: {user.id}, username: {user.username}, email: {user.email}")

        # JWT 토큰 쌍 생성
        access_token, refresh_token = auth_service.create_token_pair(
            data={"user_id": user.id, "email": user.email}
        )

        # 성공 시 프론트엔드 콜백 페이지로 리디렉션
        response = RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?success=true"
        )

        # 쿠키 설정 결정: DOMAIN이 설정되어 있으면 프로덕션 환경
        is_production = bool(settings.domain)
        cookie_domain = settings.domain if is_production else None

        # Access token을 HttpOnly 쿠키로 설정 (보안 강화)
        response.set_cookie(
            key="access_token",
            value=access_token,
            domain=cookie_domain,
            httponly=True,
            secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
            samesite="none" if is_production else "lax",
            max_age=24 * 60 * 60,  # 24시간
        )

        # Refresh token을 HttpOnly 쿠키로 설정
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            domain=cookie_domain,
            httponly=True,
            secure=is_production,  # 프로덕션(DOMAIN 설정시)에서만 secure=True
            samesite="none" if is_production else "lax",
            max_age=30 * 24 * 60 * 60,  # 30일
        )

        return response

    except OAuthError as e:
        # OAuth 에러 시에도 프론트엔드로 리디렉션
        print(f"OAuth Error: {str(e)}")
        error_message = f"Google OAuth 인증 실패: {str(e)}"
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?error={error_message}"
        )
    except Exception as e:
        # 일반 에러 시에도 프론트엔드로 리디렉션
        print(f"General Error in OAuth callback: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        error_message = f"Google 로그인 처리 중 오류가 발생했습니다: {str(e)}"
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?error={error_message}"
        )
