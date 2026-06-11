"""add question_feedback table

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-06-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("exam_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.String(length=10), nullable=False),
        sa.Column("reason_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["generated_exam.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["generated_question.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_question_feedback_user_question"),
    )
    op.create_index(op.f("ix_question_feedback_exam_id"), "question_feedback", ["exam_id"], unique=False)
    op.create_index(op.f("ix_question_feedback_question_id"), "question_feedback", ["question_id"], unique=False)
    op.create_index(op.f("ix_question_feedback_user_id"), "question_feedback", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_question_feedback_user_id"), table_name="question_feedback")
    op.drop_index(op.f("ix_question_feedback_question_id"), table_name="question_feedback")
    op.drop_index(op.f("ix_question_feedback_exam_id"), table_name="question_feedback")
    op.drop_table("question_feedback")
