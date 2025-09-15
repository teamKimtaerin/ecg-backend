"""
GPU 렌더링 작업 관리 서비스
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.render_job import RenderJob, RenderStatus
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class RenderService:
    """GPU 렌더링 작업 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create_render_job(
        self,
        video_url: str,
        scenario: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        video_name: Optional[str] = None,
    ) -> RenderJob:
        """새 렌더링 작업 생성"""
        try:
            job_id = str(uuid.uuid4())

            # 예상 시간 계산 (비디오 길이 기반)
            # TODO: 실제 비디오 길이에 따라 계산
            estimated_time = 30  # 기본 30초

            render_job = RenderJob(
                job_id=job_id,
                status=RenderStatus.QUEUED,
                progress=0,
                video_url=video_url,
                scenario=scenario,
                options=options or {},
                estimated_time=estimated_time,
                estimated_time_remaining=estimated_time,
                user_id=user_id,
                video_name=video_name,
            )

            self.db.add(render_job)
            self.db.commit()
            self.db.refresh(render_job)

            logger.info(f"렌더링 작업 생성됨 - Job ID: {job_id}")
            return render_job

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"렌더링 작업 생성 실패: {str(e)}")
            raise Exception(f"렌더링 작업 생성 실패: {str(e)}")

    def get_render_job(self, job_id: str) -> Optional[RenderJob]:
        """렌더링 작업 조회"""
        try:
            job = self.db.query(RenderJob).filter(RenderJob.job_id == job_id).first()
            return job
        except SQLAlchemyError as e:
            logger.error(f"렌더링 작업 조회 실패: {str(e)}")
            return None

    def update_render_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        download_url: Optional[str] = None,
        file_size: Optional[int] = None,
        duration: Optional[float] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        estimated_time_remaining: Optional[int] = None,
    ) -> bool:
        """렌더링 작업 상태 업데이트"""
        try:
            job = self.db.query(RenderJob).filter(RenderJob.job_id == job_id).first()

            if not job:
                logger.warning(f"존재하지 않는 Job ID: {job_id}")
                return False

            # 상태 업데이트
            if status is not None:
                job.status = status

                # 상태 변경에 따른 타임스탬프 업데이트
                if status == RenderStatus.PROCESSING and job.started_at is None:
                    job.started_at = datetime.now()
                elif status in [RenderStatus.COMPLETED, RenderStatus.FAILED]:
                    job.completed_at = datetime.now()

            if progress is not None:
                job.progress = progress

            if download_url is not None:
                job.download_url = download_url

            if file_size is not None:
                job.file_size = file_size

            if duration is not None:
                job.duration = duration

            if error_message is not None:
                job.error_message = error_message

            if error_code is not None:
                job.error_code = error_code

            if estimated_time_remaining is not None:
                job.estimated_time_remaining = estimated_time_remaining

            job.updated_at = datetime.now()

            self.db.commit()
            logger.info(f"렌더링 작업 상태 업데이트됨 - Job ID: {job_id}, Status: {status}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"렌더링 작업 상태 업데이트 실패: {str(e)}")
            return False

    def cancel_render_job(self, job_id: str) -> bool:
        """렌더링 작업 취소"""
        try:
            job = self.db.query(RenderJob).filter(RenderJob.job_id == job_id).first()

            if not job:
                logger.warning(f"존재하지 않는 Job ID: {job_id}")
                return False

            # 이미 완료되거나 실패한 작업은 취소할 수 없음
            if job.status in [RenderStatus.COMPLETED, RenderStatus.FAILED]:
                logger.warning(f"취소할 수 없는 상태 - Job ID: {job_id}, Status: {job.status}")
                return False

            job.status = RenderStatus.CANCELLED
            job.updated_at = datetime.now()

            self.db.commit()
            logger.info(f"렌더링 작업 취소됨 - Job ID: {job_id}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"렌더링 작업 취소 실패: {str(e)}")
            return False

    def list_render_jobs(
        self,
        user_id: Optional[str] = None,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[RenderJob]:
        """렌더링 작업 목록 조회"""
        try:
            query = self.db.query(RenderJob)

            if user_id:
                query = query.filter(RenderJob.user_id == user_id)

            if status:
                query = query.filter(RenderJob.status == status)

            jobs = query.order_by(RenderJob.created_at.desc()).limit(limit).all()
            return jobs

        except SQLAlchemyError as e:
            logger.error(f"렌더링 작업 목록 조회 실패: {str(e)}")
            return []

    def get_render_job_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """렌더링 작업 이력 조회"""
        try:
            query = self.db.query(RenderJob)

            if user_id:
                query = query.filter(RenderJob.user_id == user_id)

            # 완료되거나 실패한 작업만 조회
            query = query.filter(
                RenderJob.status.in_([RenderStatus.COMPLETED, RenderStatus.FAILED])
            )

            jobs = query.order_by(RenderJob.created_at.desc()).limit(limit).all()

            history = []
            for job in jobs:
                history.append({
                    "jobId": str(job.job_id),
                    "videoName": job.video_name or "Untitled",
                    "status": job.status,
                    "createdAt": job.created_at.isoformat() if job.created_at else None,
                    "completedAt": job.completed_at.isoformat() if job.completed_at else None,
                    "downloadUrl": job.download_url,
                    "fileSize": job.file_size,
                    "duration": job.duration,
                })

            return history

        except SQLAlchemyError as e:
            logger.error(f"렌더링 작업 이력 조회 실패: {str(e)}")
            return []

    def delete_render_job(self, job_id: str) -> bool:
        """렌더링 작업 삭제"""
        try:
            job = self.db.query(RenderJob).filter(RenderJob.job_id == job_id).first()

            if not job:
                logger.warning(f"존재하지 않는 Job ID: {job_id}")
                return False

            self.db.delete(job)
            self.db.commit()
            logger.info(f"렌더링 작업 삭제됨 - Job ID: {job_id}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"렌더링 작업 삭제 실패: {str(e)}")
            return False