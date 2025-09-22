#!/usr/bin/env python3
from app.db.database import SessionLocal
from app.models.plugin_asset import PluginAsset
from sqlalchemy import text

db = SessionLocal()
try:
    # Check if table exists
    result = db.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='plugin_assets')"
        )
    )
    table_exists = result.fetchone()[0]
    print(f"Table exists: {table_exists}")

    # Check data count
    count = db.query(PluginAsset).count()
    print(f"Total plugin assets: {count}")

    if count > 0:
        assets = db.query(PluginAsset).limit(3).all()
        print("Sample assets:")
        for asset in assets:
            print(f"- {asset.title} ({asset.plugin_key})")
    else:
        print("No assets found")

finally:
    db.close()
