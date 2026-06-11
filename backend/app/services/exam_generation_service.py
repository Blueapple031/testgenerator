"""LLM 기반 문제 생성 (RAG 컨텍스트 + 족보 스타일 프로필 반영)."""

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra.llm_client import openai_client
from app.models.concept import QuestionConcept
from app.models.document import StudyDocument
from app.models.exam import ExamGenerationJob, GeneratedExam, GeneratedQuestion
from app.models.exam_style import ExamStyleProfile
from app.schemas.exam import ExamGenerationRequest, GeneratedQuestionPayload
from app.services.rag_service import ChunkHit, RagService

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    "multiple_choice": "객관식",
    "short_answer": "단답형",
    "essay_short": "짧은 서술형",
    "essay_long": "긴 서술형",
}


class ExamGenerationService:
    @classmethod
    async def validate_documents(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
    ) -> list[StudyDocument]:
        result = await db.execute(
            select(StudyDocument).where(
                StudyDocument.user_id == user_id,
                StudyDocument.id.in_(document_ids),
            )
        )
        documents = list(result.scalars().all())
        if len(documents) != len(document_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="일부 문서를 찾을 수 없습니다.",
            )
        not_ready = [d.filename for d in documents if d.status != "READY"]
        if not_ready:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"인덱싱이 완료되지 않은 문서: {', '.join(not_ready)}",
            )
        return documents

    @classmethod
    async def load_style_profile(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        profile_id: uuid.UUID | None,
    ) -> ExamStyleProfile | None:
        if profile_id is None:
            return None
        result = await db.execute(
            select(ExamStyleProfile).where(
                ExamStyleProfile.id == profile_id,
                ExamStyleProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="출제 스타일 프로필을 찾을 수 없습니다.",
            )
        return profile

    @staticmethod
    def build_rag_query(request: ExamGenerationRequest) -> str:
        types = ", ".join(TYPE_LABELS.get(t, t) for t in request.question_types)
        return (
            f"시험 문제 생성: {types}, 난이도 {request.difficulty}, "
            f"{request.question_count}문항, 강의자료 핵심 개념"
        )

    @classmethod
    async def fetch_context_chunks(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        request: ExamGenerationRequest,
    ) -> list[ChunkHit]:
        return await RagService.search(
            db,
            user_id,
            request.document_ids,
            cls.build_rag_query(request),
            top_k=settings.EXAM_GEN_RAG_TOP_K,
            page_start=request.page_range_start,
            page_end=request.page_range_end,
        )

    @staticmethod
    def format_chunks_for_prompt(chunks: list[ChunkHit]) -> str:
        parts: list[str] = []
        for chunk in chunks:
            page = f"p.{chunk.page_start}" if chunk.page_start else "p.?"
            parts.append(f"[chunk_id={chunk.chunk_id} {page}]\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _pick_question_type(request: ExamGenerationRequest, index: int) -> str:
        return request.question_types[index % len(request.question_types)]

    @staticmethod
    def _normalize_choices(raw: list[dict] | None) -> list[dict] | None:
        if not raw:
            return None
        normalized: list[dict] = []
        for item in raw:
            normalized.append(
                {
                    "label": item.get("label", ""),
                    "text": item.get("text", ""),
                    "isAnswer": item.get("isAnswer", item.get("is_answer", False)),
                }
            )
        return normalized

    @classmethod
    async def generate_one_question(
        cls,
        request: ExamGenerationRequest,
        chunks: list[ChunkHit],
        question_number: int,
        question_type: str,
        style_profile: ExamStyleProfile | None,
        previous_stems: list[str],
    ) -> GeneratedQuestionPayload:
        context = cls.format_chunks_for_prompt(chunks)
        chunk_ids = [str(c.chunk_id) for c in chunks[:5]]

        style_section = ""
        if style_profile:
            style_section = (
                "\n\n[족보 출제 스타일 프로필 — 반영]\n"
                f"- 유형 분포: {style_profile.type_distribution}\n"
                f"- Bloom 분포: {style_profile.bloom_distribution}\n"
                f"- 주요 개념: {style_profile.common_concepts}\n"
                f"- 스타일 메모: {style_profile.style_notes or '없음'}"
            )

        avoid = ""
        if previous_stems:
            avoid = "\n\n이미 생성된 문제(중복 금지):\n" + "\n".join(
                f"- {s[:80]}..." if len(s) > 80 else f"- {s}" for s in previous_stems[-5:]
            )

        system_prompt = (
            "당신은 대학 강의자료에 근거해 시험 문제를 만드는 출제 전문가입니다. "
            "반드시 제공된 강의자료 chunk만 근거로 사용하고, JSON만 출력하세요."
        )
        user_prompt = f"""다음 강의자료를 근거로 시험 문제 1개를 생성하세요.

[요구사항]
- 문제 번호: {question_number}
- 문제 유형: {question_type} ({TYPE_LABELS.get(question_type, question_type)})
- 난이도: {request.difficulty}
- 객관식이면 보기 4개(A~D), 정답 1개, 오개념 기반 오답 포함
- concepts: 영문 snake_case 개념 태그 1~3개
{style_section}{avoid}

[강의자료 chunks]
{context}

[출력 JSON 스키마]
{{
  "stem": "문제 지문",
  "question_type": "{question_type}",
  "difficulty": "{request.difficulty}",
  "bloom_level": "remember|understand|apply|analyze|evaluate|create",
  "choices": [{{"label":"A","text":"...","isAnswer":false}}] 또는 null,
  "answer": "정답",
  "explanation": "해설",
  "concepts": ["concept_a"]
}}

참고 chunk id 후보: {", ".join(chunk_ids)}"""

        response = await openai_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            data["question_type"] = question_type
            data["difficulty"] = request.difficulty
            data["choices"] = cls._normalize_choices(data.get("choices"))
            return GeneratedQuestionPayload.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM JSON 검증 실패: %s — raw=%s", exc, raw[:200])
            raise ValueError(f"문제 JSON 검증 실패: {exc}") from exc

    @classmethod
    async def run_job(cls, db: AsyncSession, job: ExamGenerationJob) -> uuid.UUID:
        """Job 전체 파이프라인: RAG → LLM 생성 → DB 저장. exam_id 반환."""
        from app.services.job_service import JobService

        job_id = job.id
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

        request = ExamGenerationRequest.model_validate(job.options or {})
        await JobService.update_progress_by_id(job_id, "GENERATING", 5, "문서 검증 중...")
        await cls.validate_documents(db, job.user_id, request.document_ids)
        style_profile = await cls.load_style_profile(
            db, job.user_id, request.exam_style_profile_id
        )

        await JobService.update_progress_by_id(job_id, "GENERATING", 10, "RAG 검색 중...")
        chunks = await cls.fetch_context_chunks(db, job.user_id, request)
        if not chunks:
            raise RuntimeError("RAG 검색 결과가 없습니다. 문서 인덱싱을 확인하세요.")

        title = request.title or f"생성 문제집 {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
        exam = GeneratedExam(
            job_id=job.id,
            user_id=job.user_id,
            title=title,
            question_count=request.question_count,
        )
        db.add(exam)
        await db.flush()

        previous_stems: list[str] = []
        for i in range(request.question_count):
            qtype = cls._pick_question_type(request, i)
            pct = 15 + int((i / request.question_count) * 70)
            await JobService.update_progress_by_id(
                job_id,
                "GENERATING",
                pct,
                f"문제 {i + 1}/{request.question_count} 생성 중...",
            )
            payload = await cls.generate_one_question(
                request,
                chunks,
                i + 1,
                qtype,
                style_profile,
                previous_stems,
            )
            previous_stems.append(payload.stem)

            source_ids = [str(c.chunk_id) for c in chunks[:3]]
            question = GeneratedQuestion(
                exam_id=exam.id,
                number=i + 1,
                question_type=payload.question_type,
                difficulty=payload.difficulty,
                bloom_level=payload.bloom_level,
                stem=payload.stem,
                choices=payload.choices,
                answer=payload.answer,
                explanation=payload.explanation,
                source_chunk_ids=source_ids,
            )
            db.add(question)
            await db.flush()
            for concept in payload.concepts[:5]:
                db.add(QuestionConcept(question_id=question.id, concept=concept[:200]))

        await JobService.update_progress_by_id(job_id, "FINALIZING", 92, "문제집 저장 중...")
        await db.commit()
        return exam.id
