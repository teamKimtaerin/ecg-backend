"""
Job 상태 관리 서비스 (PostgreSQL 기반)
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.job import Job, JobStatus
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class JobService:
    """Job 상태 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        job_id: Optional[str] = None,
        status: str = JobStatus.PROCESSING,
        progress: int = 0,
        video_url: Optional[str] = None,
        file_key: Optional[str] = None,
    ) -> Job:
        """새 작업 생성"""
        try:
            if job_id is None:
                job_id = str(uuid.uuid4())

            job = Job(
                job_id=job_id,
                status=status,
                progress=progress,
                video_url=video_url,
                file_key=file_key,
            )

            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

            logger.info(f"새 작업 생성됨 - Job ID: {job_id}")
            return job

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"작업 생성 실패: {str(e)}")
            raise Exception(f"작업 생성 실패: {str(e)}")

    def get_job(self, job_id: str) -> Optional[Job]:
        """작업 조회"""
        try:
            job = self.db.query(Job).filter(Job.job_id == job_id).first()
            return job
        except SQLAlchemyError as e:
            logger.error(f"작업 조회 실패: {str(e)}")
            return None

    def update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """작업 상태 업데이트"""
        try:
            job = self.db.query(Job).filter(Job.job_id == job_id).first()

            if not job:
                logger.warning(f"존재하지 않는 Job ID: {job_id}")
                return False

            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if result is not None:
                job.result = result
            if error_message is not None:
                job.error_message = error_message

            job.updated_at = datetime.now()

            self.db.commit()
            logger.info(f"작업 상태 업데이트됨 - Job ID: {job_id}, Status: {status}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"작업 상태 업데이트 실패: {str(e)}")
            return False

    def list_all_jobs(self, limit: int = 100) -> List[Job]:
        """모든 작업 목록 조회 (최신 순)"""
        try:
            jobs = self.db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
            return jobs
        except SQLAlchemyError as e:
            logger.error(f"작업 목록 조회 실패: {str(e)}")
            return []

    def delete_job(self, job_id: str) -> bool:
        """작업 삭제"""
        try:
            job = self.db.query(Job).filter(Job.job_id == job_id).first()

            if not job:
                logger.warning(f"존재하지 않는 Job ID: {job_id}")
                return False

            self.db.delete(job)
            self.db.commit()
            logger.info(f"작업 삭제됨 - Job ID: {job_id}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"작업 삭제 실패: {str(e)}")
            return False
