"""FULL_CONTEXT 벤치마크: PDF 전체 텍스트 → LLM 1회 배치 생성."""

import json
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra.llm_client import openai_client
from app.models.concept import QuestionConcept
from app.models.exam import ExamGenerationJob, GeneratedExam, GeneratedQuestion
from app.models.exam_style import ExamStyleProfile
from app.schemas.exam import ExamGenerationRequest, GeneratedQuestionPayload
from app.services.document_text_service import DocumentTextService
from app.services.exam_generation_service import ExamGenerationService, TYPE_LABELS

logger = logging.getLogger(__name__)


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


class ExamFullContextService:
    @classmethod
    async def run_job(cls, db: AsyncSession, job: ExamGenerationJob) -> uuid.UUID:
        from app.services.job_service import JobService

        job_id = job.id
        request = ExamGenerationRequest.model_validate(job.options or {})

        await JobService.update_progress_by_id(job_id, "GENERATING", 5, "문서 확인 중...")
        documents = await DocumentTextService.load_documents(
            db,
            job.user_id,
            request.document_ids,
            require_indexed=False,
        )
        style_profile: ExamStyleProfile | None = None
        if request.exam_style_profile_id:
            style_profile = await ExamGenerationService.load_style_profile(
                db, job.user_id, request.exam_style_profile_id
            )

        await JobService.update_progress_by_id(
            job_id, "GENERATING", 15, "PDF 텍스트 추출 중..."
        )
        context, was_truncated = await DocumentTextService.build_combined_context(
            documents,
            page_start=request.page_range_start,
            page_end=request.page_range_end,
        )
        truncate_note = " (본문 일부 잘림)" if was_truncated else ""
        logger.info(
            "Job %s FULL_CONTEXT: %d자%s",
            job_id,
            len(context),
            truncate_note,
        )

        await JobService.update_progress_by_id(
            job_id,
            "GENERATING",
            35,
            f"LLM 배치 생성 중...{truncate_note}",
        )
        payloads = await cls._generate_batch(request, context, style_profile)

        base_title = request.title or f"생성 문제집 {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
        title = f"[FULL] {base_title}" if not base_title.startswith("[FULL]") else base_title

        exam = GeneratedExam(
            job_id=job.id,
            user_id=job.user_id,
            title=title,
            question_count=len(payloads),
        )
        db.add(exam)
        await db.flush()

        for index, payload in enumerate(payloads, start=1):
            question = GeneratedQuestion(
                exam_id=exam.id,
                number=index,
                question_type=payload.question_type,
                difficulty=payload.difficulty,
                bloom_level=payload.bloom_level,
                stem=payload.stem,
                choices=payload.choices,
                answer=payload.answer,
                explanation=payload.explanation,
                source_chunk_ids=None,
            )
            db.add(question)
            await db.flush()
            for concept in (payload.concepts or [])[:5]:
                db.add(
                    QuestionConcept(question_id=question.id, concept=str(concept)[:200])
                )

        await JobService.update_progress_by_id(job_id, "FINALIZING", 92, "문제집 저장 중...")
        await db.commit()
        logger.info("Job %s FULL_CONTEXT 완료: %d문항", job_id, len(payloads))
        return exam.id

    @classmethod
    async def _generate_batch(
        cls,
        request: ExamGenerationRequest,
        context: str,
        style_profile: ExamStyleProfile | None,
    ) -> list[GeneratedQuestionPayload]:
        types = ", ".join(TYPE_LABELS.get(t, t) for t in request.question_types)
        type_mix = cls._type_mix_instruction(request)

        style_section = ""
        if style_profile:
            style_section = f"""
[족보 출제 스타일]
- 유형 분포: {style_profile.type_distribution}
- Bloom: {style_profile.bloom_distribution}
- 주요 개념: {style_profile.common_concepts}
- 메모: {style_profile.style_notes or '없음'}"""

        system_prompt = (
            "당신은 대학 강의자료 PDF 본문만 보고 시험 문제를 만드는 출제 전문가입니다. "
            "제공된 텍스트 범위를 벗어난 내용은 쓰지 마세요. JSON만 출력하세요."
        )
        user_prompt = f"""아래 강의자료 전체 본문을 읽고 시험 문제 {request.question_count}개를 한 번에 생성하세요.

[생성 조건]
- 문항 수: 정확히 {request.question_count}개
- 허용 유형: {types}
{type_mix}
- 난이도: {request.difficulty}
- 정의·설명형 stem에는 개념명만 answer로 두지 말고 서술형 모범답 작성
- 객관식은 보기 4개(A~D), 정답 1개
- 문항 간 concept 중복 최소화
{style_section}

[강의자료 본문]
{context}

[출력 JSON]
{{
  "questions": [
    {{
      "stem": "문제 지문",
      "question_type": "essay_short",
      "difficulty": "{request.difficulty}",
      "bloom_level": "understand",
      "choices": null,
      "answer": "모범답",
      "explanation": "해설",
      "concepts": ["개념"]
    }}
  ]
}}"""

        response = await openai_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=settings.EXAM_GEN_BASE_TEMPERATURE,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            batch = _BatchResponsePayload.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("FULL_CONTEXT JSON 검증 실패: %s", exc)
            raise ValueError(f"배치 문제 JSON 검증 실패: {exc}") from exc

        if not batch.questions:
            raise ValueError("LLM이 문항을 반환하지 않았습니다.")

        allowed = set(request.question_types)
        results: list[GeneratedQuestionPayload] = []
        for idx, item in enumerate(batch.questions[: request.question_count]):
            qtype = item.question_type if item.question_type in allowed else request.question_types[
                idx % len(request.question_types)
            ]
            payload = GeneratedQuestionPayload(
                stem=item.stem,
                question_type=qtype,  # type: ignore[arg-type]
                difficulty=request.difficulty,
                bloom_level=item.bloom_level,
                choices=ExamGenerationService._normalize_choices(item.choices),
                answer=item.answer,
                explanation=item.explanation,
                concepts=item.concepts,
            )
            results.append(payload)

        if len(results) < request.question_count:
            logger.warning(
                "FULL_CONTEXT: 요청 %d문항 중 %d문항만 파싱됨",
                request.question_count,
                len(results),
            )
        return results

    @staticmethod
    def _type_mix_instruction(request: ExamGenerationRequest) -> str:
        lines = ["- 유형 배분 (순환):"]
        for i in range(request.question_count):
            t = request.question_types[i % len(request.question_types)]
            lines.append(f"  {i + 1}번: {TYPE_LABELS.get(t, t)} ({t})")
        return "\n".join(lines)
