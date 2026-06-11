"""시험 생성 파이프라인 내부 스키마 (Job 메모리 전용, DB 저장 없음)."""

import uuid
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

ESSAY_TYPES = frozenset({"essay_short", "essay_long"})
SHORT_TYPES = frozenset({"short_answer", "multiple_choice"})

QUESTION_ANGLES = frozenset({
    "definition",
    "comparison",
    "scenario",
    "cause_effect",
    "design",
    "tradeoff",
})

# 정의·비교·원인 등 서술이 필요한 출제 각도 — short_answer/multiple_choice와 조합 불가
ESSAY_REQUIRED_ANGLES = frozenset({
    "definition",
    "comparison",
    "cause_effect",
    "design",
    "tradeoff",
})


class AnswerCandidatePayload(BaseModel):
    """LLM 정답 후보 추출 JSON 검증용."""

    concept: str = Field(..., min_length=2)
    answer_phrase: str | None = None
    answer_outline: list[str] = Field(default_factory=list)
    evidence_chunk_id: str
    evidence_text: str = Field(..., min_length=3)
    question_type_hint: Literal["multiple_choice", "short_answer", "essay_short", "essay_long"] = (
        "short_answer"
    )
    question_angle: str = "definition"
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

    @field_validator("question_angle")
    @classmethod
    def normalize_angle(cls, value: str) -> str:
        lowered = value.lower().strip()
        return lowered if lowered in QUESTION_ANGLES else "definition"

    @model_validator(mode="after")
    def validate_type_fields(self) -> Self:
        angle = self.question_angle
        if angle in ESSAY_REQUIRED_ANGLES:
            if self.question_type_hint not in ESSAY_TYPES:
                raise ValueError(
                    f"출제 각도 '{angle}'는 essay_short/essay_long과만 조합 가능"
                )
            if len(self.answer_outline) < 2:
                raise ValueError(f"각도 '{angle}' 후보는 answer_outline 2개 이상 필요")
            return self
        if self.question_type_hint in ESSAY_TYPES:
            if len(self.answer_outline) < 2:
                raise ValueError("서술형 후보는 answer_outline 2개 이상 필요")
        elif self.question_type_hint in SHORT_TYPES:
            if not self.answer_phrase or not self.answer_phrase.strip():
                raise ValueError("단답/객관식 후보는 answer_phrase 필요")
            if normalize_text(self.answer_phrase) == normalize_text(self.concept):
                raise ValueError(
                    "answer_phrase는 concept명과 동일하면 안 됨 — 실제 정답 키워드/값을 사용"
                )
        return self


def normalize_text(text: str) -> str:
    """후보 검증용 간단 정규화 (dedup 모듈과 동일 규칙)."""
    import re

    lowered = text.lower().strip()
    return re.sub(r"[\s\W_]+", "", lowered, flags=re.UNICODE)


class AnswerCandidate(BaseModel):
    """Job 내부에서 사용하는 정답 후보 (candidate_id는 추출 후 부여)."""

    candidate_id: str
    concept: str
    answer_phrase: str = ""
    answer_outline: list[str] = Field(default_factory=list)
    evidence_chunk_id: uuid.UUID
    evidence_text: str
    question_type_hint: str
    question_angle: str = "definition"
    bloom_level: str | None = None


class QuestionValidationResult(BaseModel):
    is_valid: bool
    reason: str = ""


class GeneratedQuestionRecord(BaseModel):
    """Job 내 이미 생성·승인된 문항 (중복 검사용)."""

    stem: str
    answer: str
    concepts: list[str] = Field(default_factory=list)
    question_angle: str | None = None
    stem_embedding: list[float] | None = None
    concept_embeddings: list[list[float]] | None = None
