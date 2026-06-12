"""FULL_CONTEXT / PDF_DIRECT 공통 배치 문제 생성."""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.schemas.exam import ExamGenerationRequest, GeneratedQuestionPayload
from app.services.exam_batch_prompt import build_batch_user_prompt

logger = logging.getLogger(__name__)

__all__ = ["build_batch_user_prompt", "generate_batch_from_messages", "parse_batch_response"]


class _BatchQuestionPayload(BaseModel):
    stem: str = Field(..., min_length=5)
    question_type: str
    difficulty: str = "medium"
    bloom_level: str | None = None
    choices: list[dict] | None = None
    answer: str = Field(..., min_length=1)
    explanation: str | None = None
    concepts: list[str] = Field(default_factory=list)


class _BatchResponsePayload(BaseModel):
    questions: list[_BatchQuestionPayload]


def parse_batch_response(raw: str, request: ExamGenerationRequest) -> list[GeneratedQuestionPayload]:
    from app.services.exam_generation_service import ExamGenerationService

    try:
        data = json.loads(raw)
        batch = _BatchResponsePayload.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"배치 문제 JSON 검증 실패: {exc}") from exc

    if not batch.questions:
        raise ValueError("LLM이 문항을 반환하지 않았습니다.")

    allowed = set(request.question_types)
    results: list[GeneratedQuestionPayload] = []
    for idx, item in enumerate(batch.questions[: request.question_count]):
        qtype = (
            item.question_type
            if item.question_type in allowed
            else request.question_types[idx % len(request.question_types)]
        )
        results.append(
            GeneratedQuestionPayload(
                stem=item.stem,
                question_type=qtype,  # type: ignore[arg-type]
                difficulty=request.difficulty,
                bloom_level=item.bloom_level,
                choices=ExamGenerationService._normalize_choices(item.choices),
                answer=item.answer,
                explanation=item.explanation,
                concepts=item.concepts,
            )
        )

    if len(results) < request.question_count:
        logger.warning(
            "배치 생성: 요청 %d문항 중 %d문항만 파싱됨",
            request.question_count,
            len(results),
        )
    return results


async def generate_batch_from_messages(
    request: ExamGenerationRequest,
    messages: list[dict[str, Any]],
) -> list[GeneratedQuestionPayload]:
    from app.infra.llm_client import openai_client
    from app.infra.usage_meter import record_chat_usage

    response = await openai_client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=settings.EXAM_GEN_BASE_TEMPERATURE,
    )
    record_chat_usage(response)
    raw = response.choices[0].message.content or "{}"
    return parse_batch_response(raw, request)
