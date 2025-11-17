"""Create initial tables

Revision ID: 001
Revises:
Create Date: 2025-10-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create videos table
    op.create_table(
        "videos",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create clips table
    op.create_table(
        "clips",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("virality_score", sa.Float(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("keywords", JSON, nullable=True),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("thumbnail_path", sa.String(), nullable=True),
        sa.Column("analysis_data", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_videos_status", "videos", ["status"])
    op.create_index("idx_clips_video_id", "clips", ["video_id"])
    op.create_index("idx_clips_virality_score", "clips", ["virality_score"])


def downgrade() -> None:
    op.drop_index("idx_clips_virality_score")
    op.drop_index("idx_clips_video_id")
    op.drop_index("idx_videos_status")
    op.drop_table("clips")
    op.drop_table("videos")
