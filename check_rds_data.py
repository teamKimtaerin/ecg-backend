#!/usr/bin/env python3
"""
Check AWS RDS plugin_assets table data
"""

from sqlalchemy import create_engine, text

# AWS RDS 연결 정보
DATABASE_URL = "postgresql://postgres:BE%25BSIZ%3CBIQi4o1%29@ecg-project-pipeline-dev-postgres.c6p4wa24mn5g.us-east-1.rds.amazonaws.com:5432/ecgdb"


def check_rds_data():
    """Check AWS RDS plugin_assets table data."""

    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check if plugin_assets table exists
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='plugin_assets')"
                )
            )
            table_exists = result.fetchone()[0]

            if not table_exists:
                print("❌ plugin_assets table does not exist in AWS RDS")
                return

            print("✅ plugin_assets table exists in AWS RDS")

            # Check data count
            result = conn.execute(text("SELECT COUNT(*) FROM plugin_assets"))
            count = result.fetchone()[0]

            print(f"📊 Total plugin assets in AWS RDS: {count}")

            if count > 0:
                # Show sample data
                result = conn.execute(
                    text("SELECT id, title, plugin_key FROM plugin_assets LIMIT 3")
                )
                assets = result.fetchall()

                print("📋 Sample assets:")
                for asset in assets:
                    print(f"  - {asset[1]} ({asset[2]})")
            else:
                print("⚠️  No data found in plugin_assets table")

    except Exception as e:
        print(f"❌ Failed to connect to AWS RDS: {e}")


if __name__ == "__main__":
    print("🔍 Checking AWS RDS plugin_assets data...")
    check_rds_data()
