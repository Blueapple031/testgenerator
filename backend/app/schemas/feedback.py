from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

FeedbackRating = Literal["up", "down"]

ALLOWED_REASON_TAGS = frozenset({
    "answer_explanation_error",
    "unclear_stem",
    "off_topic",
    "wrong_difficulty",
    "poor_choices",
})

REASON_TAG_LABELS: dict[str, str] = {
    "answer_explanation_error": "정답·해설 오류",
    "unclear_stem": "문제가 애매함",
    "off_topic": "강의와 무관함",
    "wrong_difficulty": "난이도 안 맞음",
    "poor_choices": "보기 이상함",
}


class QuestionFeedbackRequest(BaseModel):
    rating: FeedbackRating
    reason_tags: list[str] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("reason_tags")
    @classmethod
    def validate_reason_tags(cls, values: list[str]) -> list[str]:
        invalid = set(values) - ALLOWED_REASON_TAGS
        if invalid:
            raise ValueError(f"지원하지 않는 피드백 사유: {invalid}")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_down_requires_reason(self) -> "QuestionFeedbackRequest":
        if self.rating == "down" and not self.reason_tags and not (self.comment and self.comment.strip()):
            raise ValueError("별로 평가 시 사유를 하나 이상 선택하거나 코멘트를 입력해 주세요.")
        if self.rating == "up":
            self.reason_tags = []
            self.comment = None
        return self


class QuestionFeedbackResponse(BaseModel):
    id: UUID
    exam_id: UUID
    question_id: UUID
    rating: FeedbackRating
    reason_tags: list[str] = Field(default_factory=list)
    comment: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("reason_tags", mode="before")
    @classmethod
    def normalize_reason_tags(cls, value: list[str] | None) -> list[str]:
        return value or []


class ExamFeedbackListResponse(BaseModel):
    feedback: list[QuestionFeedbackResponse]
