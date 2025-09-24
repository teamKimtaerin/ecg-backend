from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AssetBase(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    plugin_key: str = Field(alias="pluginKey")
    thumbnail_path: Optional[str] = Field(
        default="assets/thumbnail.svg", alias="thumbnailPath"
    )
    icon_name: Optional[str] = Field(default=None, alias="iconName")
    author_id: str = Field(alias="authorId")
    author_name: str = Field(alias="authorName")
    is_pro: Optional[bool] = Field(default=False, alias="isPro")
    price: Optional[float] = 0.0
    rating: Optional[float] = 0.0
    downloads: Optional[int] = 0
    likes: Optional[int] = 0
    usage_count: Optional[int] = Field(default=0, alias="usageCount")
    tags: Optional[List[str]] = []
    is_favorite: Optional[bool] = Field(default=False, alias="isFavorite")


class AssetResponse(AssetBase):
    id: int
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class AssetsListResponse(BaseModel):
    assets: List[AssetResponse]


class CategoryResponse(BaseModel):
    categories: List[str]
