import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExamGenerationJob(Base):
    __tablename__ = "exam_generation_job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspace.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    options: Mapped[dict | None] = mapped_column(JSONB)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GeneratedExam(Base):
    __tablename__ = "generated_exam"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exam_generation_job.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    export_minio_key: Mapped[str | None] = mapped_column(String(500))  # 선택적 HTML PDF export 캐시
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeneratedQuestion(Base):
    __tablename__ = "generated_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generated_exam.id"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    bloom_level: Mapped[str | None] = mapped_column(String(20))
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list | None] = mapped_column(JSONB)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    source_chunk_ids: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
