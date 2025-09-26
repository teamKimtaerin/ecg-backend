#!/usr/bin/env python3
"""
Create plugin assets table and insert sample data
"""

import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine, SessionLocal
from app.models.plugin_asset import PluginAsset


def create_table_and_data():
    """Create plugin_assets table and insert sample data."""

    # Create tables
    from app.models.plugin_asset import Base

    Base.metadata.create_all(bind=engine)
    print("✅ plugin_assets table created")

    # Create session
    db = SessionLocal()

    try:
        # Check if data already exists
        existing_count = db.query(PluginAsset).count()
        if existing_count > 0:
            print(
                f"⚠️  Found {existing_count} existing assets, skipping data insertion"
            )
            return

        # Sample plugin assets data
        sample_assets = [
            {
                "title": "Rotation Text",
                "category": "Dynamic",
                "description": "글자들이 회전하면서 나타나는 클래식한 애니메이션 효과입니다.",
                "plugin_key": "rotation@2.0.0",
                "thumbnail_path": "assets/thumbnail.svg",
                "icon_name": "IoRefresh",
                "author_id": "ecg-team",
                "author_name": "HOIT Team",
                "is_pro": False,
                "price": 0.0,
                "rating": 5.0,
                "downloads": 1243,
                "likes": 892,
                "usage_count": 2156,
                "tags": ["text", "rotation", "spin", "classic", "gsap", "animation"],
            },
            {
                "title": "Slide Up Effect",
                "category": "Smooth",
                "description": "텍스트가 아래에서 부드럽게 올라오는 우아한 애니메이션입니다.",
                "plugin_key": "slideup@2.0.0",
                "thumbnail_path": "assets/thumbnail.svg",
                "icon_name": "IoArrowUp",
                "author_id": "ecg-team",
                "author_name": "HOIT Team",
                "is_pro": False,
                "price": 0.0,
                "rating": 4.8,
                "downloads": 987,
                "likes": 654,
                "usage_count": 1845,
                "tags": ["text", "slide", "smooth", "elegant", "gsap"],
            },
            {
                "title": "Bounce Animation",
                "category": "Dynamic",
                "description": "텍스트가 통통 튀는 재미있는 바운스 효과입니다.",
                "plugin_key": "bobY@2.0.0",
                "thumbnail_path": "assets/thumbnail.svg",
                "icon_name": "IoHappy",
                "author_id": "ecg-team",
                "author_name": "HOIT Team",
                "is_pro": False,
                "price": 0.0,
                "rating": 4.5,
                "downloads": 756,
                "likes": 423,
                "usage_count": 1234,
                "tags": ["text", "bounce", "fun", "playful", "gsap"],
            },
            {
                "title": "Glitch Effect Pro",
                "category": "Unique",
                "description": "디지털 글리치 효과로 현대적인 느낌을 연출합니다.",
                "plugin_key": "glitch@2.0.0",
                "thumbnail_path": "assets/thumbnail.svg",
                "icon_name": "IoFlash",
                "author_id": "ecg-team",
                "author_name": "HOIT Team",
                "is_pro": True,
                "price": 4.99,
                "rating": 4.9,
                "downloads": 432,
                "likes": 298,
                "usage_count": 876,
                "tags": ["text", "glitch", "digital", "modern", "pro"],
            },
            {
                "title": "Typewriter Effect",
                "category": "Smooth",
                "description": "클래식한 타이프라이터 효과로 텍스트를 한 글자씩 타이핑합니다.",
                "plugin_key": "typewriter@2.0.0",
                "thumbnail_path": "assets/thumbnail.svg",
                "icon_name": "IoCreate",
                "author_id": "ecg-team",
                "author_name": "HOIT Team",
                "is_pro": False,
                "price": 0.0,
                "rating": 4.7,
                "downloads": 1567,
                "likes": 1234,
                "usage_count": 2890,
                "tags": ["text", "typewriter", "classic", "typing", "gsap"],
            },
        ]

        # Insert sample data
        for asset_data in sample_assets:
            asset = PluginAsset(**asset_data)
            db.add(asset)

        db.commit()
        print(f"✅ Inserted {len(sample_assets)} plugin assets")

        # Verify insertion
        total_count = db.query(PluginAsset).count()
        print(f"📊 Total assets in database: {total_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Creating plugin assets table and data...")
    create_table_and_data()
    print("✨ Done!")
