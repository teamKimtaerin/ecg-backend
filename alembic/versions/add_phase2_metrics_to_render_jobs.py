"""Add Phase 2 streaming metrics to render_jobs table

Revision ID: add_phase2_metrics
Revises:
Create Date: 2025-01-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_phase2_metrics"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add Phase 2 streaming pipeline metrics columns"""
    # Add Phase 2 metrics columns to render_jobs table
    op.add_column(
        "render_jobs", sa.Column("frames_processed", sa.Integer(), nullable=True)
    )
    op.add_column(
        "render_jobs", sa.Column("frames_dropped", sa.Integer(), nullable=True)
    )
    op.add_column("render_jobs", sa.Column("drop_rate", sa.Float(), nullable=True))
    op.add_column("render_jobs", sa.Column("memory_peak_mb", sa.Float(), nullable=True))
    op.add_column(
        "render_jobs", sa.Column("memory_trend", sa.String(20), nullable=True)
    )

    # Create indexes for performance queries
    op.create_index("idx_render_jobs_drop_rate", "render_jobs", ["job_id", "drop_rate"])
    op.create_index(
        "idx_render_jobs_memory", "render_jobs", ["job_id", "memory_peak_mb"]
    )


def downgrade():
    """Remove Phase 2 streaming pipeline metrics columns"""
    # Drop indexes
    op.drop_index("idx_render_jobs_memory", "render_jobs")
    op.drop_index("idx_render_jobs_drop_rate", "render_jobs")

    # Drop Phase 2 metrics columns
    op.drop_column("render_jobs", "memory_trend")
    op.drop_column("render_jobs", "memory_peak_mb")
    op.drop_column("render_jobs", "drop_rate")
    op.drop_column("render_jobs", "frames_dropped")
    op.drop_column("render_jobs", "frames_processed")
