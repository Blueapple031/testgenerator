from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ALLOWED_QUESTION_TYPES = {
    "multiple_choice",
    "short_answer",
    "essay_short",
    "essay_long",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
GenerationMode = Literal["rag", "full_context", "pdf_direct"]


class ExamGenerationRequest(BaseModel):
    workspace_id: UUID | None = None
    document_ids: list[UUID] = Field(..., min_length=1)
    title: str | None = Field(default=None, max_length=300)
    question_count: int = Field(default=10, ge=1, le=30)
    question_types: list[str] = Field(default=["short_answer", "essay_short"], min_length=1)
    difficulty: str = "medium"
    bloom_distribution: dict[str, int] | None = None
    exam_style_profile_id: UUID | None = None
    page_range_start: int | None = Field(default=None, ge=1)
    page_range_end: int | None = Field(default=None, ge=1)
    toc_ids: list[UUID] | None = None
    # rag: RAG+후보 파이프라인(기본)
    # full_context: PyMuPDF 추출 텍스트 → LLM 배치
    # pdf_direct: PDF 원본 → OpenAI API 직접 입력 baseline
    generation_mode: GenerationMode = "rag"

    @field_validator("generation_mode", mode="before")
    @classmethod
    def normalize_generation_mode(cls, value: str | None) -> str:
        if value is None:
            return "rag"
        lowered = str(value).lower().strip()
        if lowered == "rag":
            return "rag"
        if lowered in ("pdf_direct", "pdf", "direct", "pdf_baseline", "baseline", "native_pdf"):
            return "pdf_direct"
        if lowered in ("full_context", "full", "fullcontext"):
            return "full_context"
        raise ValueError("generation_mode는 rag, full_context, pdf_direct 중 하나여야 합니다.")

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, values: list[str]) -> list[str]:
        invalid = set(values) - ALLOWED_QUESTION_TYPES
        if invalid:
            raise ValueError(f"지원하지 않는 문제 유형: {invalid}")
        return values

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        if value not in ALLOWED_DIFFICULTIES:
            raise ValueError(f"difficulty는 {ALLOWED_DIFFICULTIES} 중 하나여야 합니다.")
        return value


class TokenUsageSummary(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    embedding_tokens: int = 0
    llm_calls: int = 0
    embedding_calls: int = 0


class JobCreateResponse(BaseModel):
    job_id: UUID
    status: str


class JobStatusResponse(BaseModel):
    id: UUID
    status: str
    progress: int
    message: str | None
    exam_id: UUID | None = None
    token_usage: dict[str, int] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobStreamEvent(BaseModel):
    stage: str
    progress: int
    message: str | None = None
    exam_id: UUID | None = None
    token_usage: dict[str, int] | None = None


class QuestionResponse(BaseModel):
    id: UUID
    number: int
    question_type: str
    difficulty: str
    bloom_level: str | None
    stem: str
    choices: list | None
    answer: str
    explanation: str | None
    concepts: list[str] = []

    model_config = {"from_attributes": True}


class ExamListItem(BaseModel):
    id: UUID
    title: str
    question_count: int
    created_at: datetime
    token_usage: TokenUsageSummary | None = None

    model_config = {"from_attributes": True}


class ExamResponse(BaseModel):
    id: UUID
    title: str
    question_count: int
    questions: list[QuestionResponse] = []
    created_at: datetime
    token_usage: TokenUsageSummary | None = None

    model_config = {"from_attributes": True}


class GeneratedQuestionPayload(BaseModel):
    """LLM 응답 JSON 검증용."""

    stem: str = Field(..., min_length=5)
    question_type: Literal["multiple_choice", "short_answer", "essay_short", "essay_long"]
    difficulty: Literal["easy", "medium", "hard"]
    bloom_level: str | None = None
    choices: list[dict] | None = None
    answer: str = Field(..., min_length=1)
    explanation: str | None = None
    concepts: list[str] = Field(default_factory=list)
