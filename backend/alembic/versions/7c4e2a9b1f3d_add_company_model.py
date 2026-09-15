"""add company model

Revision ID: 7c4e2a9b1f3d
Revises: 2f6b8a1d4c9e
Create Date: 2026-09-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7c4e2a9b1f3d"
down_revision: Union[str, Sequence[str], None] = "2f6b8a1d4c9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    company_size = postgresql.ENUM(
        "STARTUP", "MID", "ENTERPRISE", name="company_size", create_type=False
    )
    company_size.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("website", sa.String(length=2000), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("size", company_size, nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_companies_user_id"), "companies", ["user_id"], unique=False
    )
    # Functional unique index: case-insensitive company name, per user. Not
    # expressible as a plain sa.Column unique constraint, hence the raw
    # `lower(name)` expression.
    op.create_index(
        "ix_companies_user_name_lower",
        "companies",
        ["user_id", sa.text("lower(name)")],
        unique=True,
    )

    op.add_column("applications", sa.Column("company_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_applications_company_id_companies",
        "applications",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_applications_company_id"),
        "applications",
        ["company_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_applications_company_id"), table_name="applications")
    op.drop_constraint(
        "fk_applications_company_id_companies", "applications", type_="foreignkey"
    )
    op.drop_column("applications", "company_id")

    op.drop_index("ix_companies_user_name_lower", table_name="companies")
    op.drop_index(op.f("ix_companies_user_id"), table_name="companies")
    op.drop_table("companies")

    # Drop ENUM type LAST (after the table that uses it)
    postgresql.ENUM(name="company_size", create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
