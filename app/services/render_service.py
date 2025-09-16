"""
GPU 렌더링 작업 관리 서비스
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_
from app.models.render_job import RenderJob, RenderStatus
from app.models.user import User
from app.models.render_usage_stats import RenderUsageStats
import logging
import uuid
from datetime import datetime, date

logger = logging.getLogger(__name__)


class RenderService:
    """GPU 렌더링 작업 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def check_user_quota(self, user_id: str) -> Dict[str, Any]:
        """사용자 렌더링 할당량 확인"""
        try:
            # 사용자 정보 조회
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"allowed": False, "reason": "User not found"}

            today = date.today()
            current_month_start = date(today.year, today.month, 1)

            # 오늘 렌더링 횟수
            daily_count = (
                self.db.query(RenderJob)
                .filter(
                    and_(
                        RenderJob.user_id == user_id,
                        func.date(RenderJob.created_at) == today,
                        RenderJob.status != RenderStatus.CANCELLED,
                    )
                )
                .count()
            )

            # 이번 달 렌더링 횟수
            monthly_count = (
                self.db.query(RenderJob)
                .filter(
                    and_(
                        RenderJob.user_id == user_id,
                        func.date(RenderJob.created_at) >= current_month_start,
                        RenderJob.status != RenderStatus.CANCELLED,
                    )
                )
                .count()
            )

            # 현재 진행 중인 작업 수
            concurrent_count = (
                self.db.query(RenderJob)
                .filter(
                    and_(
                        RenderJob.user_id == user_id,
                        RenderJob.status.in_(
                            [RenderStatus.QUEUED, RenderStatus.PROCESSING]
                        ),
                    )
                )
                .count()
            )

            # 할당량 체크
            if daily_count >= user.render_quota_daily:
                return {
                    "allowed": False,
                    "reason": f"Daily quota exceeded ({daily_count}/{user.render_quota_daily})",
                    "quota_type": "daily",
                }

            if monthly_count >= user.render_quota_monthly:
                return {
                    "allowed": False,
                    "reason": f"Monthly quota exceeded ({monthly_count}/{user.render_quota_monthly})",
                    "quota_type": "monthly",
                }

            if concurrent_count >= user.concurrent_render_limit:
                return {
                    "allowed": False,
                    "reason": f"Too many concurrent jobs ({concurrent_count}/{user.concurrent_render_limit})",
                    "quota_type": "concurrent",
                }

            return {
                "allowed": True,
                "daily_usage": {"used": daily_count, "limit": user.render_quota_daily},
                "monthly_usage": {
                    "used": monthly_count,
                    "limit": user.render_quota_monthly,
                },
                "concurrent_usage": {
                    "used": concurrent_count,
                    "limit": user.concurrent_render_limit,
                },
            }

        except SQLAlchemyError as e:
            logger.error(f"할당량 확인 실패: {str(e)}")
            return {"allowed": False, "reason": "Database error"}

    def create_render_job(
        self,
        video_url: str,
        scenario: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        video_name: Optional[str] = None,
        estimated_time: Optional[int] = None,
    ) -> RenderJob:
        """새 렌더링 작업 생성"""
        try:
            job_id = str(uuid.uuid4())

            # 예상 시간 사용 (기본값 30초)
            if estimated_time is None:
                estimated_time = 30

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
        status: Optional[str] = None,
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
        self, user_id: Optional[str] = None, limit: int = 10
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
                history.append(
                    {
                        "jobId": str(job.job_id),
                        "videoName": job.video_name or "Untitled",
                        "status": job.status,
                        "createdAt": job.created_at.isoformat()
                        if job.created_at
                        else None,
                        "completedAt": job.completed_at.isoformat()
                        if job.completed_at
                        else None,
                        "downloadUrl": job.download_url,
                        "fileSize": job.file_size,
                        "duration": job.duration,
                    }
                )

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

    def update_usage_stats(self, job: RenderJob) -> bool:
        """렌더링 완료 시 사용량 통계 업데이트"""
        try:
            if not job.user_id or job.status not in [
                RenderStatus.COMPLETED,
                RenderStatus.FAILED,
            ]:
                return True  # 통계 업데이트 필요 없음

            today = date.today()

            # 기존 통계 레코드 조회 또는 생성
            stats = (
                self.db.query(RenderUsageStats)
                .filter(
                    and_(
                        RenderUsageStats.user_id == job.user_id,
                        RenderUsageStats.date == today,
                    )
                )
                .first()
            )

            if not stats:
                stats = RenderUsageStats(user_id=job.user_id, date=today)
                self.db.add(stats)

            # 카운트 업데이트
            stats.render_count += 1

            if job.status == RenderStatus.COMPLETED:
                stats.render_success_count += 1

                # 성공한 경우만 시간/크기 통계 업데이트
                if job.duration:
                    stats.total_duration += job.duration

                if job.file_size:
                    stats.total_file_size += job.file_size

                # 처리 시간 계산 (started_at과 completed_at 기반)
                if job.started_at and job.completed_at:
                    processing_time = (
                        job.completed_at - job.started_at
                    ).total_seconds()
                    stats.total_processing_time += processing_time

                # Cue 개수 카운트
                if job.scenario and "cues" in job.scenario:
                    cues_count = len(job.scenario["cues"])
                    stats.total_cues_processed += cues_count

            elif job.status == RenderStatus.FAILED:
                stats.render_failed_count += 1

            # 평균값 계산
            if stats.render_success_count > 0:
                stats.avg_processing_time = (
                    stats.total_processing_time / stats.render_success_count
                )
                stats.avg_file_size = stats.total_file_size / stats.render_success_count
                stats.avg_cues_per_job = (
                    stats.total_cues_processed / stats.render_success_count
                )

            self.db.commit()
            logger.info(f"사용량 통계 업데이트됨 - User: {job.user_id}, Date: {today}")
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"사용량 통계 업데이트 실패: {str(e)}")
            return False

    def get_user_usage_stats(
        self, user_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """사용자 사용량 통계 조회"""
        try:
            end_date = date.today()
            start_date = date(end_date.year, end_date.month, end_date.day - days)

            stats = (
                self.db.query(RenderUsageStats)
                .filter(
                    and_(
                        RenderUsageStats.user_id == user_id,
                        RenderUsageStats.date >= start_date,
                        RenderUsageStats.date <= end_date,
                    )
                )
                .order_by(RenderUsageStats.date.desc())
                .all()
            )

            return [stat.to_dict() for stat in stats]

        except SQLAlchemyError as e:
            logger.error(f"사용량 통계 조회 실패: {str(e)}")
            return []
