from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
)
import json
import logging

logger = logging.getLogger(__name__)


class ProjectService:
    """프로젝트 관련 비즈니스 로직"""

    @staticmethod
    async def create_or_update_project(
        db: Session,
        user_id: int,
        project_id: str,
        project_data: ProjectCreate,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """프로젝트 생성 또는 업데이트"""

        # 기존 프로젝트 조회
        existing_project = (
            db.query(Project)
            .filter(and_(Project.id == project_id, Project.user_id == user_id))
            .first()
        )

        if existing_project:
            # 버전 충돌 체크
            if version is not None and existing_project.version != version:
                return {
                    "error": "CONFLICT",
                    "current_version": existing_project.version,
                    "your_version": version,
                    "conflict_resolution": "merge",
                }

            # 프로젝트 업데이트
            return await ProjectService._update_project(
                db, existing_project, project_data
            )
        else:
            # 새 프로젝트 생성
            return await ProjectService._create_project(db, user_id, project_data)

    @staticmethod
    async def _create_project(
        db: Session, user_id: int, project_data: ProjectCreate
    ) -> Dict[str, Any]:
        """새 프로젝트 생성"""

        try:
            # 프로젝트 생성
            new_project = Project(
                id=project_data.id,
                user_id=user_id,
                name=project_data.name,
                clips=json.loads(project_data.model_dump_json())["clips"],
                settings=project_data.settings.model_dump()
                if project_data.settings
                else {},
                media_id=project_data.media_id,
                video_url=project_data.video_url,
                video_name=project_data.video_name,
                video_type=project_data.video_type,
                video_duration=project_data.video_duration,
                video_metadata=project_data.video_metadata.model_dump()
                if project_data.video_metadata
                else None,
                version=1,
                change_count=0,
                server_synced_at=datetime.utcnow(),
                sync_status="synced",
            )

            db.add(new_project)
            db.commit()
            db.refresh(new_project)

            logger.info(f"Project created: {project_data.id}")

            return {
                "success": True,
                "synced_at": new_project.server_synced_at,
                "version": new_project.version,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project: {str(e)}",
            )

    @staticmethod
    async def _update_project(
        db: Session, project: Project, project_data: ProjectCreate
    ) -> Dict[str, Any]:
        """기존 프로젝트 업데이트"""

        try:
            # 프로젝트 정보 업데이트
            project.name = project_data.name
            project.clips = json.loads(project_data.model_dump_json())["clips"]

            if project_data.settings:
                project.settings = project_data.settings.model_dump()

            if project_data.video_url:
                project.video_url = project_data.video_url
            if project_data.video_name:
                project.video_name = project_data.video_name
            if project_data.video_type:
                project.video_type = project_data.video_type
            if project_data.video_duration:
                project.video_duration = project_data.video_duration
            if project_data.video_metadata:
                project.video_metadata = project_data.video_metadata.model_dump()

            # 버전 및 동기화 정보 업데이트
            project.version += 1
            project.change_count = 0
            project.server_synced_at = datetime.utcnow()
            project.sync_status = "synced"
            project.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(project)

            logger.info(f"Project updated: {project.id}, version: {project.version}")

            return {
                "success": True,
                "synced_at": project.server_synced_at,
                "version": project.version,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update project: {str(e)}",
            )

    @staticmethod
    async def get_project(
        db: Session, user_id: int, project_id: str
    ) -> ProjectResponse:
        """프로젝트 조회"""

        project = (
            db.query(Project)
            .filter(and_(Project.id == project_id, Project.user_id == user_id))
            .first()
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # ProjectResponse 형식으로 변환
        return ProjectResponse(
            id=project.id,
            name=project.name,
            clips=project.clips or [],
            settings=project.settings or {},
            video_url=project.video_url,
            video_name=project.video_name,
            video_type=project.video_type,
            video_duration=project.video_duration,
            video_metadata=project.video_metadata,
            created_at=project.created_at,
            updated_at=project.updated_at,
            server_synced_at=project.server_synced_at,
            sync_status=project.sync_status,
            version=project.version,
            change_count=project.change_count,
        )

    @staticmethod
    async def list_projects(
        db: Session,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        sort: str = "updated_at:desc",
    ) -> Dict[str, Any]:
        """프로젝트 목록 조회"""

        # 정렬 파싱
        sort_field, sort_order = sort.split(":")

        # 쿼리 생성
        query = db.query(Project).filter(Project.user_id == user_id)

        # 정렬 적용
        if sort_order == "desc":
            query = query.order_by(getattr(Project, sort_field).desc())
        else:
            query = query.order_by(getattr(Project, sort_field))

        # 전체 개수
        total = query.count()

        # 페이지네이션
        offset = (page - 1) * limit
        projects = query.offset(offset).limit(limit).all()

        # 응답 형식 변환
        project_list = []
        for project in projects:
            # 클립 개수 계산
            clip_count = len(project.clips) if project.clips else 0

            # 프로젝트 크기 계산 (대략적)
            project_size = len(json.dumps(project.clips or [])) if project.clips else 0

            project_list.append(
                ProjectListResponse(
                    id=project.id,
                    name=project.name,
                    last_modified=project.updated_at,
                    size=project_size,
                    clip_count=clip_count,
                    video_duration=project.video_duration,
                    sync_status=project.sync_status,
                )
            )

        return {"projects": project_list, "total": total, "page": page, "limit": limit}

    @staticmethod
    async def delete_project(
        db: Session, user_id: int, project_id: str
    ) -> Dict[str, Any]:
        """프로젝트 삭제"""

        project = (
            db.query(Project)
            .filter(and_(Project.id == project_id, Project.user_id == user_id))
            .first()
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        try:
            db.delete(project)
            db.commit()

            logger.info(f"Project deleted: {project_id}")

            return {"success": True, "message": "Project deleted successfully"}

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete project: {str(e)}",
            )

    @staticmethod
    async def export_project(
        db: Session, user_id: int, project_id: str, format: str = "srt"
    ) -> str:
        """프로젝트를 자막 파일 형식으로 내보내기"""

        project = await ProjectService.get_project(db, user_id, project_id)

        if not project.clips:
            return ""

        # SRT 형식으로 변환
        if format == "srt":
            return ProjectService._export_as_srt(project.clips)
        elif format == "vtt":
            return ProjectService._export_as_vtt(project.clips)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}",
            )

    @staticmethod
    def _export_as_srt(clips: List[Dict]) -> str:
        """SRT 형식으로 내보내기"""
        srt_content = []

        for idx, clip in enumerate(clips, 1):
            # 시간 형식 변환
            words = clip.get("words", [])
            if words:
                start_time = ProjectService._seconds_to_srt_time(words[0]["start"])
                end_time = ProjectService._seconds_to_srt_time(words[-1]["end"])
                text = clip.get("fullText", clip.get("subtitle", ""))

                srt_content.append(f"{idx}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")  # 빈 줄

        return "\n".join(srt_content)

    @staticmethod
    def _export_as_vtt(clips: List[Dict]) -> str:
        """VTT 형식으로 내보내기"""
        vtt_content = ["WEBVTT", ""]

        for clip in clips:
            words = clip.get("words", [])
            if words:
                start_time = ProjectService._seconds_to_vtt_time(words[0]["start"])
                end_time = ProjectService._seconds_to_vtt_time(words[-1]["end"])
                text = clip.get("fullText", clip.get("subtitle", ""))

                vtt_content.append(f"{start_time} --> {end_time}")
                vtt_content.append(text)
                vtt_content.append("")  # 빈 줄

        return "\n".join(vtt_content)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """초를 SRT 시간 형식으로 변환 (00:00:00,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        """초를 VTT 시간 형식으로 변환 (00:00:00.000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
