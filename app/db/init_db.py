"""
데이터베이스 초기화 스크립트
SQLAlchemy 모델 기반으로 테이블 생성 + 시드 데이터 추가
"""

from app.db.database import engine, Base
from app.db.seed_data import create_seed_data
import logging

logger = logging.getLogger(__name__)


def init_database():
    """
    데이터베이스 초기화
    1. SQLAlchemy 모델 기반으로 테이블 생성
    2. 시드 데이터 추가
    """
    try:
        logger.info("Initializing database...")

        # 1. 테이블 생성 (SQLAlchemy 모델 기반)
        logger.info("Creating tables from SQLAlchemy models...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")

        # 2. 시드 데이터 생성
        logger.info("Creating seed data...")
        create_seed_data()

        logger.info("Database initialization completed!")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


if __name__ == "__main__":
    # 직접 실행 시
    logging.basicConfig(level=logging.INFO)
    init_database()
