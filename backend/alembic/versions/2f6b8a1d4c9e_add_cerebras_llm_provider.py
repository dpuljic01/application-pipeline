"""add cerebras llm provider

Revision ID: 2f6b8a1d4c9e
Revises: 11381511e77a
Create Date: 2026-09-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f6b8a1d4c9e"
down_revision: Union[str, Sequence[str], None] = "11381511e77a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres 12+ allows ALTER TYPE ... ADD VALUE inside a transaction block
    # (this only *adds* the label — it isn't used by any row in this same
    # migration, which is the one thing that still isn't allowed).
    op.execute("ALTER TYPE llm_provider_name ADD VALUE IF NOT EXISTS 'CEREBRAS'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing a label requires
    # rebuilding the type (rename old, create new without it, migrate the
    # column, drop old) — not worth the risk for a downgrade path. No-op;
    # rows using 'CEREBRAS' would need manual cleanup first if this is ever
    # actually rolled back.
    pass
