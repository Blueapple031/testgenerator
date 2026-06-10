from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExamGenerationRequest(BaseModel):
    workspace_id: UUID | None = None
    document_ids: list[UUID]
    question_count: int = 10
    question_types: list[str] = ["short_answer"]
    difficulty: str = "medium"
    bloom_distribution: dict[str, int] | None = None
    exam_style_profile_id: UUID | None = None
    page_range_start: int | None = None
    page_range_end: int | None = None
    toc_ids: list[UUID] | None = None


class JobStatusResponse(BaseModel):
    id: UUID
    status: str
    progress: int
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


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


class ExamResponse(BaseModel):
    id: UUID
    title: str
    question_count: int
    questions: list[QuestionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
