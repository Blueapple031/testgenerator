from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExamStyleAnalyzeRequest(BaseModel):
    document_id: UUID
    professor_name: str | None = Field(default=None, max_length=100)
    subject: str | None = Field(default=None, max_length=200)
    raw_text: str | None = Field(
        default=None,
        max_length=50_000,
        description="PDF 추출 대신 직접 입력한 족보 텍스트 (선택)",
    )


class ExamStyleProfileResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_filename: str | None = None
    professor_name: str | None
    subject: str | None
    analyzed_exam_count: int
    type_distribution: dict[str, int] | None
    bloom_distribution: dict[str, int] | None
    avg_questions_per_exam: int | None
    common_concepts: list[str] | None
    style_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StyleAnalysisPayload(BaseModel):
    """LLM 족보 분석 JSON 검증용."""

    professor_name: str | None = None
    subject: str | None = None
    type_distribution: dict[str, int]
    bloom_distribution: dict[str, int]
    avg_questions_per_exam: int = Field(..., ge=1, le=200)
    common_concepts: list[str] = Field(default_factory=list)
    style_notes: str | None = None
