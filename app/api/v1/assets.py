from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional
from app.db.database import get_db
from app.models.plugin_asset import PluginAsset
from app.schemas.asset import AssetResponse, AssetsListResponse, CategoryResponse

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("/", response_model=AssetsListResponse)
async def get_assets(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_pro: Optional[bool] = Query(None, description="Filter by pro status"),
    limit: Optional[int] = Query(100, description="Maximum number of assets to return"),
    offset: Optional[int] = Query(0, description="Number of assets to skip"),
    db: Session = Depends(get_db),
):
    """
    퍼블릭 에셋 목록 조회 API (인증 불필요)
    - 모든 사용자가 로그인 없이 에셋 목록을 볼 수 있음
    - 카테고리 및 프로 상태로 필터링 가능
    """
    try:
        query = db.query(PluginAsset)

        # 필터 적용
        if category:
            query = query.filter(PluginAsset.category == category)

        if is_pro is not None:
            query = query.filter(PluginAsset.is_pro == is_pro)

        # 정렬 및 페이지네이션
        assets = (
            query.order_by(PluginAsset.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return AssetsListResponse(assets=assets)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch assets: {str(e)}")


@router.get("/categories", response_model=CategoryResponse)
async def get_categories(db: Session = Depends(get_db)):
    """
    사용 가능한 카테고리 목록 조회 API (인증 불필요)
    """
    try:
        categories = db.query(distinct(PluginAsset.category)).all()
        category_list = [category[0] for category in categories if category[0]]

        return CategoryResponse(categories=category_list)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch categories: {str(e)}"
        )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_detail(asset_id: int, db: Session = Depends(get_db)):
    """
    특정 에셋 상세 정보 조회 API (인증 불필요)
    """
    try:
        asset = db.query(PluginAsset).filter(PluginAsset.id == asset_id).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        return asset

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch asset detail: {str(e)}"
        )
