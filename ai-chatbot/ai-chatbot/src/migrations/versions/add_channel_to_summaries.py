"""Add channel column to conversation_summaries

Revision ID: c4e7a2f1b3d9
Revises: b1f1c9a3da8e
Create Date: 2025-01-01 00:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e7a2f1b3d9"
down_revision: str | Sequence[str] | None = "b1f1c9a3da8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversation_summaries",
        sa.Column("channel", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_summaries", "channel")
