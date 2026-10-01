"""drop cerebras from llm_provider_name

Revision ID: cf45892ce602
Revises: 4dac2530e1b7
Create Date: 2026-10-01 14:59:27.518806

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cf45892ce602"
down_revision: Union[str, Sequence[str], None] = "4dac2530e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    in_use = bind.scalar(
        sa.text("SELECT count(*) FROM llm_usage WHERE provider = 'CEREBRAS'")
    )
    if in_use:
        raise RuntimeError(
            f"{in_use} llm_usage rows still reference CEREBRAS - delete or "
            "relabel them before dropping the enum value"
        )

    # Postgres has no ALTER TYPE ... DROP VALUE: rebuild the type without it.
    op.execute("ALTER TYPE llm_provider_name RENAME TO llm_provider_name_old")
    op.execute("CREATE TYPE llm_provider_name AS ENUM ('GEMINI', 'ANTHROPIC')")
    op.execute(
        "ALTER TABLE llm_usage ALTER COLUMN provider TYPE llm_provider_name "
        "USING provider::text::llm_provider_name"
    )
    op.execute("DROP TYPE llm_provider_name_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE llm_provider_name ADD VALUE IF NOT EXISTS 'CEREBRAS'")
