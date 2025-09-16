"""
개발용 시드 데이터
docker-compose up 시 자동으로 실행되는 초기 데이터
"""

from app.models.user import AuthProvider
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.db.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


def create_seed_data():
    """시드 데이터 생성"""
    db = SessionLocal()

    try:
        # 개발용 테스트 사용자들
        test_users = [
            {
                "username": "testuser1",
                "email": "test1@example.com",
                "password": "password123",
            },
            {"username": "admin", "email": "admin@example.com", "password": "admin123"},
            {"username": "demo", "email": "demo@example.com", "password": "demo1234"},
        ]

        created_count = 0

        for user_data in test_users:
            # 이미 존재하는 사용자는 건너뛰기
            if not auth_service.get_user_by_email(db, user_data["email"]):
                user_create = UserCreate(**user_data)
                auth_service.create_user(db, user_create)
                created_count += 1
                logger.info(f"Created test user: {user_data['email']}")
            else:
                logger.info(f"User already exists: {user_data['email']}")

        # OAuth 테스트 사용자 (Google)
        oauth_users = [
            {
                "username": "google_user",
                "email": "googletest@gmail.com",
                "oauth_id": "google_123456789",
                "provider": AuthProvider.GOOGLE,
            }
        ]

        for oauth_data in oauth_users:
            if not auth_service.get_user_by_oauth_id(
                db, oauth_data["oauth_id"], oauth_data["provider"]
            ):
                auth_service.create_oauth_user(
                    db=db,
                    email=oauth_data["email"],
                    username=oauth_data["username"],
                    oauth_id=oauth_data["oauth_id"],
                    provider=oauth_data["provider"],
                )
                created_count += 1
                logger.info(f"Created OAuth user: {oauth_data['email']}")

        logger.info(f"Seed data creation completed. Created {created_count} users.")

    except Exception as e:
        logger.error(f"Error creating seed data: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # 직접 실행 시
    logging.basicConfig(level=logging.INFO)
    create_seed_data()
