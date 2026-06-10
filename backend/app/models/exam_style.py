import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExamStyleProfile(Base):
    __tablename__ = "exam_style_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("study_document.id"), nullable=False)
    professor_name: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(200))
    analyzed_exam_count: Mapped[int] = mapped_column(Integer, default=1)
    type_distribution: Mapped[dict | None] = mapped_column(JSONB)
    bloom_distribution: Mapped[dict | None] = mapped_column(JSONB)
    avg_questions_per_exam: Mapped[int | None] = mapped_column(Integer)
    common_concepts: Mapped[list | None] = mapped_column(JSONB)
    style_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
