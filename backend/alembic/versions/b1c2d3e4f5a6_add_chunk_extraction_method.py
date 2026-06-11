"""add extraction_method to document_chunk

Revision ID: b1c2d3e4f5a6
Revises: 2fae44ffc7c5
Create Date: 2026-06-11 06:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "2fae44ffc7c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunk",
        sa.Column(
            "extraction_method",
            sa.String(length=20),
            nullable=False,
            server_default="text",
        ),
    )


def downgrade() -> None:
    op.drop_column("document_chunk", "extraction_method")
