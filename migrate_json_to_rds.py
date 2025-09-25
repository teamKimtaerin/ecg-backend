#!/usr/bin/env python3
"""
Migrate JSON assets data to AWS RDS plugin_assets table
"""

import os
import sys
import json
from datetime import datetime
from dateutil import parser

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine, SessionLocal
from app.models.plugin_asset import PluginAsset


def migrate_json_to_rds():
    """Migrate JSON assets data to AWS RDS plugin_assets table."""

    # JSON 파일 경로
    json_file_path = "../ecg-frontend/public/asset-store/assets-database.json"

    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        return

    # JSON 데이터 읽기
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assets_data = data.get("assets", [])
    print(f"📋 Found {len(assets_data)} assets in JSON file")

    # Create tables if not exist
    from app.models.plugin_asset import Base

    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Check if data already exists
        existing_count = db.query(PluginAsset).count()
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing assets in RDS")
            response = input("Clear existing data and migrate? (y/N): ")
            if response.lower() != "y":
                print("Migration cancelled")
                return

            # Clear existing data
            db.query(PluginAsset).delete()
            db.commit()
            print("🗑️  Cleared existing data")

        # Migrate each asset
        migrated_count = 0
        for asset_data in assets_data:
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

                print(
                    f"✅ Migrated: {asset_data.get('title')} ({asset_data.get('pluginKey')})"
                )

            except Exception as e:
                print(
                    f"❌ Failed to migrate asset {asset_data.get('title', 'Unknown')}: {e}"
                )
                continue

        # Commit all changes
        db.commit()
        print(f"🎉 Successfully migrated {migrated_count} assets to AWS RDS")

        # Verify migration
        total_count = db.query(PluginAsset).count()
        print(f"📊 Total assets in RDS: {total_count}")

        # Show sample records
        samples = db.query(PluginAsset).limit(3).all()
        print("\n📋 Sample migrated records:")
        for asset in samples:
            print(f"  - {asset.title} ({asset.plugin_key}) - {asset.category}")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting JSON to RDS migration...")
    migrate_json_to_rds()
    print("✨ Migration completed!")
