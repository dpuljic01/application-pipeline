"""add pipeline status to applications

Revision ID: 4dac2530e1b7
Revises: eef13d98d1c0
Create Date: 2026-10-01 14:54:51.912069

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4dac2530e1b7"
down_revision: Union[str, Sequence[str], None] = "eef13d98d1c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pipeline_status = postgresql.ENUM(
        "PENDING", "COMPLETED", "FAILED", name="pipeline_status", create_type=False
    )
    pipeline_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "applications",
        sa.Column("pipeline_status", pipeline_status, nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("pipeline_error", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("applications", "pipeline_error")
    op.drop_column("applications", "pipeline_status")

    # Drop ENUM type LAST (after the column that uses it)
    postgresql.ENUM(name="pipeline_status", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
