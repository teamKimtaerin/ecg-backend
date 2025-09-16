"""
Redis 클라이언트 설정
"""

import redis
from typing import Optional, Any, Dict
import json
import os

# Redis 연결 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "20"))
REDIS_DECODE_RESPONSES = True
REDIS_SOCKET_TIMEOUT = 5
REDIS_SOCKET_CONNECT_TIMEOUT = 5

# Connection Pool 생성 (재사용을 위해)
redis_pool = redis.ConnectionPool.from_url(
    REDIS_URL,
    max_connections=REDIS_POOL_SIZE,
    decode_responses=REDIS_DECODE_RESPONSES,
    socket_timeout=REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
)


class RedisClient:
    """Redis 클라이언트 래퍼 (Read-Only: GPU Server가 Single Source of Truth)"""

    def __init__(self):
        self.client = redis.Redis(connection_pool=redis_pool, decode_responses=True)

    # ❌ 제거된 Write 메서드들 (GPU Server 전용)
    # - set_job_data(): GPU Server에서만 작업 데이터 저장
    # - update_job_field(): GPU Server에서만 필드 업데이트
    # - set_worker_status(): GPU Server에서만 워커 상태 설정
    # - set_render_progress(): GPU Server에서만 진행률 업데이트
    # - update_render_metrics(): GPU Server에서만 메트릭 업데이트

    def get_job_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """작업 데이터 조회 (GPU Server가 저장한 데이터 읽기)"""
        try:
            key = f"job:{job_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get job data error: {e}")
            return None

    def get_worker_status(
        self, job_id: str, worker_id: int
    ) -> Optional[Dict[str, Any]]:
        """단일 Worker 상태 조회 (GPU Server가 설정한 상태 읽기)"""
        try:
            key = f"worker:{job_id}:{worker_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get worker status error: {e}")
            return None

    def get_all_worker_status(
        self, job_id: str, worker_count: int = 4
    ) -> Dict[int, Dict]:
        """모든 Worker 상태 조회 (GPU Server가 설정한 상태들 읽기)"""
        try:
            statuses = {}
            for i in range(worker_count):
                status = self.get_worker_status(job_id, i)
                if status:
                    statuses[i] = status
                else:
                    # GPU Server가 아직 설정하지 않은 경우 기본값
                    statuses[i] = {"status": "pending", "progress": 0}
            return statuses
        except Exception as e:
            print(f"Redis get all worker status error: {e}")
            return {}

    def get_render_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """렌더링 진행률 조회 (GPU Server가 업데이트한 진행률 읽기)"""
        try:
            key = f"render_progress:{job_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get render progress error: {e}")
            return None

    def get_render_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Phase 2 메트릭 조회 (GPU Server가 업데이트한 메트릭 읽기)"""
        try:
            key = f"render_metrics:{job_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get metrics error: {e}")
            return None

    def delete_job_data(self, job_id: str) -> bool:
        """작업 데이터 삭제"""
        try:
            # Job 데이터 삭제
            self.client.delete(f"job:{job_id}")

            # Worker 상태 삭제
            for i in range(4):
                self.client.delete(f"worker:{job_id}:{i}")

            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    def ping(self) -> bool:
        """Redis 연결 확인"""
        try:
            return self.client.ping()
        except Exception:
            return False


# 싱글톤 인스턴스
redis_client = RedisClient()
