from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 연결 확인
    pool_size=10,  # 연결 풀 크기
    max_overflow=20,  # 최대 오버플로우
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성 (모든 모델이 상속받을 클래스)
Base = declarative_base()


# 데이터베이스 세션 의존성
def get_db():
    """FastAPI 의존성 주입용 데이터베이스 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
