"""add user_id to videos table

Revision ID: 004
Revises: 003
Create Date: 2025-12-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to videos table for tracking ownership."""
    op.add_column(
        "videos",
        sa.Column("user_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_videos_user_id",
        "videos",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_videos_user_id", "videos", ["user_id"])
    op.create_index("ix_videos_created_at", "videos", ["created_at"])


def downgrade() -> None:
    """Remove user_id column from videos table."""
    op.drop_index("ix_videos_created_at", table_name="videos")
    op.drop_index("ix_videos_user_id", table_name="videos")
    op.drop_constraint("fk_videos_user_id", "videos", type_="foreignkey")
    op.drop_column("videos", "user_id")
