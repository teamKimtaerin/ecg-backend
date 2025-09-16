#!/usr/bin/env python3
"""
Jobs 테이블 생성 스크립트 (PostgreSQL)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_config():
    """환경 변수에서 데이터베이스 설정 가져오기"""
    return {
        "host": os.getenv(
            "DB_HOST",
            "ecg-project-pipeline-dev-postgres.c6p4wa24mn5g.us-east-1.rds.amazonaws.com",
        ),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "ecgdb"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "BE%BSIZ<BIQi4o1)"),
    }


def create_jobs_table():
    """Jobs 테이블 생성"""

    # 테이블 생성 SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id UUID PRIMARY KEY,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        progress INTEGER DEFAULT 0,
        video_url TEXT,
        file_key TEXT,
        result JSONB,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- 인덱스 추가 (성능 향상)
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
    """

    try:
        # 데이터베이스 연결
        db_config = get_db_config()
        logger.info(f"데이터베이스 연결 중: {db_config['host']}:{db_config['port']}")

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 테이블 생성
        logger.info("Jobs 테이블 생성 중...")
        cursor.execute(create_table_sql)

        # 테이블 목록 확인
        cursor.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """
        )

        tables = [row["tablename"] for row in cursor.fetchall()]
        logger.info(f"현재 테이블 목록: {tables}")

        # 테이블 구조 확인
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'jobs'
            ORDER BY ordinal_position;
        """
        )

        columns = cursor.fetchall()
        logger.info("Jobs 테이블 구조:")
        for col in columns:
            logger.info(
                f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})"
            )

        # 변경 사항 커밋
        conn.commit()
        logger.info("✅ Jobs 테이블이 성공적으로 생성되었습니다!")

        return True

    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {str(e)}")
        if "conn" in locals():
            conn.rollback()
        return False

    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()
        logger.info("데이터베이스 연결 종료")


if __name__ == "__main__":
    success = create_jobs_table()
    sys.exit(0 if success else 1)
