from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.db.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.project_service import ProjectService
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.put("/{project_id}")
async def create_or_update_project(
    project_id: str,
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    if_match: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    프로젝트 생성 또는 업데이트

    - 새 프로젝트를 생성하거나 기존 프로젝트를 업데이트합니다.
    - If-Match 헤더로 버전 충돌을 감지합니다.
    """
    # If-Match 헤더에서 버전 추출
    version = None
    if if_match:
        try:
            version = int(if_match)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid If-Match header format",
            )

    # 프로젝트 ID 일치 확인
    if project_id != project_data.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID mismatch"
        )

    result = await ProjectService.create_or_update_project(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        project_data=project_data,
        version=version,
    )

    # 충돌 발생 시 409 반환
    if "error" in result and result["error"] == "CONFLICT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)

    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    프로젝트 조회

    특정 프로젝트의 전체 데이터를 가져옵니다.
    """
    return await ProjectService.get_project(
        db=db, user_id=current_user.id, project_id=project_id
    )


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query(
        "updated_at:desc", regex="^(updated_at|created_at|name):(asc|desc)$"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    프로젝트 목록 조회

    사용자의 모든 프로젝트 목록을 페이지네이션과 함께 조회합니다.

    - page: 페이지 번호 (기본값: 1)
    - limit: 페이지당 항목 수 (기본값: 20, 최대: 100)
    - sort: 정렬 기준 (updated_at:desc, created_at:asc, name:asc)
    """
    return await ProjectService.list_projects(
        db=db, user_id=current_user.id, page=page, limit=limit, sort=sort
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    프로젝트 삭제

    프로젝트와 관련된 모든 데이터를 삭제합니다.
    """
    return await ProjectService.delete_project(
        db=db, user_id=current_user.id, project_id=project_id
    )


@router.get("/{project_id}/export")
async def export_project(
    project_id: str,
    format: str = Query("srt", regex="^(srt|vtt|ass)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    프로젝트 내보내기

    프로젝트를 자막 파일 형식으로 내보냅니다.

    - format: 출력 형식 (srt, vtt, ass)
    """
    content = await ProjectService.export_project(
        db=db, user_id=current_user.id, project_id=project_id, format=format
    )

    # 파일 확장자와 MIME 타입 설정
    if format == "srt":
        media_type = "text/srt"
        filename = f"{project_id}.srt"
    elif format == "vtt":
        media_type = "text/vtt"
        filename = f"{project_id}.vtt"
    elif format == "ass":
        media_type = "text/x-ssa"
        filename = f"{project_id}.ass"
    else:
        media_type = "text/plain"
        filename = f"{project_id}.txt"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch("/{project_id}/clips")
async def update_project_clips(
    project_id: str,
    clips_update: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    프로젝트 클립 증분 업데이트

    변경된 클립만 전송하여 네트워크 최적화

    Request Body:
    {
        "added": [...],     # 추가된 클립
        "modified": [...],  # 수정된 클립
        "deleted": [...]    # 삭제된 클립 ID
    }
    """
    # TODO: 증분 업데이트 로직 구현
    # Phase 2에서 구현 예정
    return {"message": "Incremental update will be implemented in Phase 2"}
