"""add pilot auth fields to users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("invite_code", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("token_quota", sa.BigInteger(), nullable=True))
    op.add_column(
        "users",
        sa.Column("tokens_used", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_index(op.f("ix_users_invite_code"), "users", ["invite_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_invite_code"), table_name="users")
    op.drop_column("users", "is_active")
    op.drop_column("users", "tokens_used")
    op.drop_column("users", "token_quota")
    op.drop_column("users", "invite_code")
