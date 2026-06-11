"""시험 생성 파이프라인 내부 스키마 (Job 메모리 전용, DB 저장 없음)."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_BLOOM_LEVELS = {
    "remember",
    "understand",
    "understanding",
    "apply",
    "analyze",
    "evaluate",
    "create",
}


class AnswerCandidatePayload(BaseModel):
    """LLM 정답 후보 추출 JSON 검증용."""

    concept: str = Field(..., min_length=2)
    answer_phrase: str = Field(..., min_length=1)
    evidence_chunk_id: str
    evidence_text: str = Field(..., min_length=3)
    question_type_hint: Literal["multiple_choice", "short_answer", "essay_short", "essay_long"] = (
        "short_answer"
    )
    bloom_level: str | None = None

    @field_validator("bloom_level")
    @classmethod
    def normalize_bloom(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower().strip()
        if lowered == "understanding":
            return "understand"
        return lowered


class AnswerCandidate(BaseModel):
    """Job 내부에서 사용하는 정답 후보 (candidate_id는 추출 후 부여)."""

    candidate_id: str
    concept: str
    answer_phrase: str
    evidence_chunk_id: uuid.UUID
    evidence_text: str
    question_type_hint: str
    bloom_level: str | None = None


class QuestionValidationResult(BaseModel):
    is_valid: bool
    reason: str = ""


class GeneratedQuestionRecord(BaseModel):
    """Job 내 이미 생성·승인된 문항 (중복 검사용)."""

    stem: str
    answer: str
    concepts: list[str] = Field(default_factory=list)
    stem_embedding: list[float] | None = None
    concept_embeddings: list[list[float]] | None = None
