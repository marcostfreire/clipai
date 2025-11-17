"""add oauth and subscription fields to users

Revision ID: 003
Revises: 002
Create Date: 2025-11-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OAuth and subscription fields to users table."""
    # Make hashed_password nullable
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=True
    )

    # Add new columns
    op.add_column("users", sa.Column("oauth_provider", sa.String(), nullable=True))
    op.add_column("users", sa.Column("oauth_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier", sa.String(), server_default="free", nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_status", sa.String(), server_default="active", nullable=True
        ),
    )
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column(
        "users", sa.Column("stripe_subscription_id", sa.String(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove OAuth and subscription fields from users table."""
    op.drop_column("users", "updated_at")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_tier")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "full_name")
    op.drop_column("users", "oauth_id")
    op.drop_column("users", "oauth_provider")

    # Make hashed_password non-nullable again
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=False
    )
