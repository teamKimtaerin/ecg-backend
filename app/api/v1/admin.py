from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.plugin_asset import PluginAsset
from datetime import datetime
from dateutil import parser

router = APIRouter(prefix="/admin", tags=["admin"])

# Sample JSON data for migration (same as assets-database.json)
SAMPLE_ASSETS_DATA = [
    {
        "id": "1",
        "title": "Rotation Text",
        "category": "Dynamic",
        "description": "글자들이 회전하면서 나타나는 클래식한 애니메이션 효과입니다.",
        "pluginKey": "rotation@2.0.0",
        "thumbnailPath": "assets/thumbnail.svg",
        "iconName": "IoRefresh",
        "authorId": "ecg-team",
        "authorName": "HOIT Team",
        "isPro": False,
        "price": 0.0,
        "rating": 5.0,
        "downloads": 1243,
        "likes": 892,
        "usageCount": 2156,
        "tags": ["text", "rotation", "spin", "classic", "gsap", "animation"],
        "isFavorite": True,
        "createdAt": "2024-01-15T08:30:00",
        "updatedAt": "2024-02-01T14:22:00",
    },
    {
        "id": "2",
        "title": "TypeWriter Effect",
        "category": "Smooth",
        "description": "타자기처럼 글자가 하나씩 나타나는 부드러운 타이핑 애니메이션입니다.",
        "pluginKey": "typewriter@2.0.0",
        "thumbnailPath": "assets/thumbnail.svg",
        "iconName": "IoDocument",
        "authorId": "ecg-team",
        "authorName": "HOIT Team",
        "isPro": False,
        "price": 0.0,
        "rating": 4.0,
        "downloads": 856,
        "likes": 654,
        "usageCount": 1423,
        "tags": ["text", "typing", "typewriter", "sequential", "gsap", "animation"],
        "isFavorite": False,
        "createdAt": "2024-01-20T10:15:00",
        "updatedAt": "2024-02-05T09:45:00",
    }
    # Add more assets as needed...
]


@router.post("/migrate-assets")
async def migrate_assets(db: Session = Depends(get_db)):
    """Migrate sample assets data to plugin_assets table."""

    try:
        # Check existing data
        existing_count = db.query(PluginAsset).count()

        if existing_count > 0:
            return {
                "message": f"Assets already exist ({existing_count} records). Migration skipped.",
                "existing_count": existing_count,
            }

        # Migrate sample data
        migrated_count = 0

        for asset_data in SAMPLE_ASSETS_DATA:
            try:
                # Convert JSON field names to database column names
                db_data = {
                    "id": asset_data.get("id"),
                    "title": asset_data.get("title"),
                    "category": asset_data.get("category"),
                    "description": asset_data.get("description"),
                    "plugin_key": asset_data.get("pluginKey"),
                    "thumbnail_path": asset_data.get(
                        "thumbnailPath", "assets/thumbnail.svg"
                    ),
                    "icon_name": asset_data.get("iconName"),
                    "author_id": asset_data.get("authorId"),
                    "author_name": asset_data.get("authorName"),
                    "is_pro": asset_data.get("isPro", False),
                    "price": float(asset_data.get("price", 0)),
                    "rating": float(asset_data.get("rating", 0)),
                    "downloads": int(asset_data.get("downloads", 0)),
                    "likes": int(asset_data.get("likes", 0)),
                    "usage_count": int(asset_data.get("usageCount", 0)),
                    "tags": asset_data.get("tags", []),
                    "is_favorite": asset_data.get("isFavorite", False),
                }

                # Parse timestamps
                if asset_data.get("createdAt"):
                    try:
                        db_data["created_at"] = parser.parse(asset_data["createdAt"])
                    except (ValueError, TypeError):
                        db_data["created_at"] = datetime.utcnow()

                if asset_data.get("updatedAt"):
                    try:
                        db_data["updated_at"] = parser.parse(asset_data["updatedAt"])
                    except (ValueError, TypeError):
                        db_data["updated_at"] = datetime.utcnow()

                # Create PluginAsset instance
                asset = PluginAsset(**db_data)
                db.add(asset)
                migrated_count += 1

            except Exception as e:
                print(
                    f"Failed to migrate asset {asset_data.get('title', 'Unknown')}: {e}"
                )
                continue

        # Commit all changes
        db.commit()

        # Verify migration
        total_count = db.query(PluginAsset).count()

        return {
            "message": f"Successfully migrated {migrated_count} assets",
            "migrated_count": migrated_count,
            "total_count": total_count,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")


@router.get("/check-assets")
async def check_assets(db: Session = Depends(get_db)):
    """Check plugin_assets table data."""

    try:
        count = db.query(PluginAsset).count()

        result = {"total_count": count, "assets": []}

        if count > 0:
            # Get sample records
            assets = db.query(PluginAsset).limit(5).all()
            result["assets"] = [
                {
                    "id": asset.id,
                    "title": asset.title,
                    "plugin_key": asset.plugin_key,
                    "category": asset.category,
                }
                for asset in assets
            ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {e}")
