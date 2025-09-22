from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from sqlalchemy.orm import Session
from app.api.v1.auth import get_current_user_optional
from app.models.user import User
from app.models.plugin_asset import PluginAsset
from app.db.database import get_db

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("")
async def get_plugin_assets(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_pro: Optional[bool] = Query(None, description="Filter by pro status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get available plugin assets based on user permissions."""
    try:
        # DB에서 plugin_assets 테이블 조회
        query = db.query(PluginAsset)

        # 카테고리 필터링
        if category:
            query = query.filter(PluginAsset.category == category)

        # Pro 필터링 - 사용자 권한에 따른 접근 제어
        if is_pro is not None:
            query = query.filter(PluginAsset.is_pro == is_pro)
        elif not current_user:
            # 로그인하지 않은 사용자는 무료 에셋만 볼 수 있음
            query = query.filter(PluginAsset.is_pro == False)

        # TODO: 향후 사용자별 Pro 권한 체크 로직 추가
        # if current_user and not current_user.is_pro:
        #     query = query.filter(PluginAsset.is_pro == False)

        assets = query.all()

        # 모델을 딕셔너리로 변환
        assets_data = [asset.to_dict() for asset in assets]

        return {"assets": assets_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))