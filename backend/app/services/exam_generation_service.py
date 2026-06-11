"""LLM 기반 문제 생성 (정답 후보 → 후보별 생성 → 검증·중복 제거)."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra.embedding_client import get_embeddings
from app.infra.llm_client import openai_client
from app.models.concept import QuestionConcept
from app.models.document import StudyDocument
from app.models.exam import ExamGenerationJob, GeneratedExam, GeneratedQuestion
from app.models.exam_style import ExamStyleProfile
from app.schemas.exam import ExamGenerationRequest, GeneratedQuestionPayload
from app.schemas.exam_generation import (
    AnswerCandidate,
    AnswerCandidatePayload,
    GeneratedQuestionRecord,
)
from app.services.exam_generation_dedup import (
    deduplicate_candidates,
    is_duplicate_question,
    resolve_chunk_id,
    select_candidate_for_question,
    validate_generated_question,
)
from app.services.rag_service import ChunkHit, RagService

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    "multiple_choice": "객관식",
    "short_answer": "단답형",
    "essay_short": "짧은 서술형",
    "essay_long": "긴 서술형",
}


@dataclass
class _JobGenerationState:
    chunk_usage_count: dict[str, int] = field(default_factory=dict)
    used_candidate_ids: set[str] = field(default_factory=set)
    generated_questions: list[GeneratedQuestionRecord] = field(default_factory=list)


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
            f"{request.question_count}문항, 강의자료 핵심 개념 정의 공식 비교"
        )

    @classmethod
    async def retrieve_candidate_chunks(
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
    def _chunk_map(chunks: list[ChunkHit]) -> dict[uuid.UUID, ChunkHit]:
        return {c.chunk_id: c for c in chunks}

    @staticmethod
    def format_chunks_for_prompt(chunks: list[ChunkHit]) -> str:
        parts: list[str] = []
        for chunk in chunks:
            page = f"p.{chunk.page_start}" if chunk.page_start else "p.?"
            parts.append(f"[chunk_id={chunk.chunk_id} {page}]\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _candidate_count(request: ExamGenerationRequest) -> int:
        return max(
            request.question_count * settings.EXAM_GEN_CANDIDATE_MULTIPLIER,
            settings.EXAM_GEN_MIN_CANDIDATE_COUNT,
        )

    @staticmethod
    def _pick_question_type(request: ExamGenerationRequest, index: int) -> str:
        return request.question_types[index % len(request.question_types)]

    @staticmethod
    def _normalize_choices(raw: list[dict] | None) -> list[dict] | None:
        if not raw:
            return None
        return [
            {
                "label": item.get("label", ""),
                "text": item.get("text", ""),
                "isAnswer": item.get("isAnswer", item.get("is_answer", False)),
            }
            for item in raw
        ]

    @classmethod
    async def extract_answer_candidates(
        cls,
        chunks: list[ChunkHit],
        request: ExamGenerationRequest,
        candidate_count: int,
    ) -> list[AnswerCandidate]:
        context = cls.format_chunks_for_prompt(chunks)
        chunk_id_list = ", ".join(str(c.chunk_id) for c in chunks)
        types = ", ".join(request.question_types)

        system_prompt = (
            "당신은 대학 강의자료에서 시험 출제 가능한 정답 후보를 추출하는 전문가입니다. "
            "제공된 chunk만 근거로 사용하고 JSON만 출력하세요."
        )
        user_prompt = f"""다음 강의자료 chunk에서 출제 가능한 정답 후보를 {candidate_count}개 추출하세요.

[요구사항]
- 서로 다른 핵심 개념(concept)을 다룰 것
- answer_phrase는 chunk 원문에 근거한 짧은 정답
- evidence_chunk_id는 아래 chunk_id 중 하나
- evidence_text는 해당 chunk에서 정답 근거가 되는 문장
- question_type_hint: {types} 중 하나
- bloom_level: remember|understand|apply|analyze|evaluate|create

[chunk id 목록]
{chunk_id_list}

[강의자료 chunks]
{context}

[출력 JSON]
{{
  "candidates": [
    {{
      "concept": "핵심 개념",
      "answer_phrase": "정답 후보",
      "evidence_chunk_id": "uuid",
      "evidence_text": "근거 문장",
      "question_type_hint": "short_answer",
      "bloom_level": "understand"
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
            raw_candidates = data.get("candidates", data if isinstance(data, list) else [])
            valid_ids = {c.chunk_id for c in chunks}
            mapped: list[AnswerCandidate] = []
            for idx, item in enumerate(raw_candidates):
                payload = AnswerCandidatePayload.model_validate(item)
                chunk_uuid = resolve_chunk_id(payload.evidence_chunk_id, valid_ids)
                if chunk_uuid is None:
                    chunk_uuid = chunks[idx % len(chunks)].chunk_id
                mapped.append(
                    AnswerCandidate(
                        candidate_id=f"cand_{idx}_{uuid.uuid4().hex[:8]}",
                        concept=payload.concept,
                        answer_phrase=payload.answer_phrase,
                        evidence_chunk_id=chunk_uuid,
                        evidence_text=payload.evidence_text,
                        question_type_hint=payload.question_type_hint,
                        bloom_level=payload.bloom_level,
                    )
                )
            return mapped
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("정답 후보 JSON 검증 실패: %s", exc)
            raise ValueError(f"정답 후보 추출 실패: {exc}") from exc

    @classmethod
    def select_chunks_for_candidate(
        cls,
        candidate: AnswerCandidate,
        all_chunks: list[ChunkHit],
        chunk_map: dict[uuid.UUID, ChunkHit],
        chunk_usage_count: dict[str, int],
    ) -> list[ChunkHit]:
        """evidence chunk + 사용 횟수가 적은 주변 chunk."""
        max_chunks = settings.EXAM_GEN_MAX_CONTEXT_CHUNKS
        selected: list[ChunkHit] = []
        seen: set[uuid.UUID] = set()

        evidence = chunk_map.get(candidate.evidence_chunk_id)
        if evidence:
            selected.append(evidence)
            seen.add(evidence.chunk_id)

        others = sorted(
            [c for c in all_chunks if c.chunk_id not in seen],
            key=lambda c: (chunk_usage_count.get(str(c.chunk_id), 0), c.chunk_index),
        )
        for chunk in others:
            if len(selected) >= max_chunks:
                break
            selected.append(chunk)
            seen.add(chunk.chunk_id)

        return selected

    @staticmethod
    def _format_previous_questions(previous: list[GeneratedQuestionRecord]) -> str:
        if not previous:
            return ""
        lines: list[str] = []
        for idx, q in enumerate(previous, start=1):
            concepts = ", ".join(q.concepts[:3]) if q.concepts else "-"
            stem = q.stem[:120] + "..." if len(q.stem) > 120 else q.stem
            answer = q.answer[:60] + "..." if len(q.answer) > 60 else q.answer
            lines.append(f"{idx}. stem: {stem} | concept: {concepts} | answer: {answer}")
        return "\n\n이미 생성된 문제(동일·유사 개념 금지):\n" + "\n".join(lines)

    @classmethod
    async def generate_one_question(
        cls,
        request: ExamGenerationRequest,
        chunks: list[ChunkHit],
        question_number: int,
        question_type: str,
        target_candidate: AnswerCandidate,
        style_profile: ExamStyleProfile | None,
        previous_questions: list[GeneratedQuestionRecord],
        *,
        temperature: float | None = None,
        retry_reason: str | None = None,
    ) -> GeneratedQuestionPayload:
        context = cls.format_chunks_for_prompt(chunks)
        chunk_ids = [str(c.chunk_id) for c in chunks]

        style_section = ""
        if style_profile:
            style_section = (
                "\n\n[족보 출제 스타일 프로필]\n"
                f"- 유형 분포: {style_profile.type_distribution}\n"
                f"- Bloom 분포: {style_profile.bloom_distribution}\n"
                f"- 주요 개념: {style_profile.common_concepts}\n"
                f"- 스타일 메모: {style_profile.style_notes or '없음'}"
            )

        retry_section = f"\n\n[이전 생성 실패 사유]\n{retry_reason}" if retry_reason else ""
        avoid = cls._format_previous_questions(previous_questions)

        system_prompt = (
            "당신은 대학 강의자료에 근거해 시험 문제를 만드는 출제 전문가입니다. "
            "지정된 핵심 개념과 정답 후보만 사용하고, JSON만 출력하세요."
        )
        user_prompt = f"""지정된 정답 후보를 기반으로 시험 문제 1개를 생성하세요.

[필수 규칙]
- 이번 문항은 아래 핵심 개념·정답 후보(answer_phrase)를 기반으로 생성
- 제공된 원문 근거(evidence_text)를 벗어난 내용 추가 금지
- 이미 생성된 문제와 동일·유사 개념 반복 금지
- 문장 표현만 바꾼 문제 금지
- 정답(answer)은 answer_phrase와 일치해야 함

[정답 후보]
- concept: {target_candidate.concept}
- answer_phrase: {target_candidate.answer_phrase}
- evidence_text: {target_candidate.evidence_text}
- bloom_level: {target_candidate.bloom_level or 'understand'}

[요구사항]
- 문제 번호: {question_number}
- 문제 유형: {question_type} ({TYPE_LABELS.get(question_type, question_type)})
- 난이도: {request.difficulty}
- 객관식이면 보기 4개(A~D), 정답 1개
- concepts 필드에 concept 반영 (snake_case 1~3개)
{style_section}{avoid}{retry_section}

[참고 chunks — chunk_id={target_candidate.evidence_chunk_id} 중심]
{context}

[출력 JSON]
{{
  "stem": "문제 지문",
  "question_type": "{question_type}",
  "difficulty": "{request.difficulty}",
  "bloom_level": "{target_candidate.bloom_level or 'understand'}",
  "choices": [{{"label":"A","text":"...","isAnswer":false}}] 또는 null,
  "answer": "{target_candidate.answer_phrase}",
  "explanation": "해설",
  "concepts": ["concept_tag"]
}}

chunk ids: {", ".join(chunk_ids)}"""

        response = await openai_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature or settings.EXAM_GEN_BASE_TEMPERATURE,
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
    async def _embed_for_dedup(
        cls,
        payload: GeneratedQuestionPayload,
        candidate: AnswerCandidate,
    ) -> tuple[list[float] | None, list[float] | None]:
        texts = [payload.stem, candidate.concept]
        try:
            vectors = await get_embeddings(texts)
            return vectors[0], vectors[1]
        except Exception:
            logger.warning("중복 검사용 embedding 실패 — 문자열 fallback 사용")
            return None, None

    @classmethod
    async def _try_generate_question(
        cls,
        request: ExamGenerationRequest,
        all_chunks: list[ChunkHit],
        chunk_map: dict[uuid.UUID, ChunkHit],
        candidates: list[AnswerCandidate],
        state: _JobGenerationState,
        question_number: int,
        question_type: str,
        style_profile: ExamStyleProfile | None,
    ) -> tuple[GeneratedQuestionPayload, AnswerCandidate, list[ChunkHit]] | None:
        max_retries = settings.EXAM_GEN_MAX_RETRIES
        last_reason = ""

        for attempt in range(max_retries):
            candidate = select_candidate_for_question(
                candidates, state.used_candidate_ids, state.chunk_usage_count
            )
            if candidate is None:
                logger.warning("문항 %d: 사용 가능한 후보 없음", question_number)
                return None

            selected_chunks = cls.select_chunks_for_candidate(
                candidate, all_chunks, chunk_map, state.chunk_usage_count
            )
            evidence = chunk_map.get(candidate.evidence_chunk_id)
            evidence_content = evidence.content if evidence else candidate.evidence_text

            temperature = (
                settings.EXAM_GEN_RETRY_TEMPERATURE
                if attempt > 0
                else settings.EXAM_GEN_BASE_TEMPERATURE
            )
            retry_reason = last_reason if attempt > 0 else None

            try:
                payload = await cls.generate_one_question(
                    request,
                    selected_chunks,
                    question_number,
                    question_type,
                    candidate,
                    style_profile,
                    state.generated_questions,
                    temperature=temperature,
                    retry_reason=retry_reason,
                )
            except ValueError as exc:
                last_reason = str(exc)
                logger.info(
                    "문항 %d 재시도 %d: 생성 실패 — %s",
                    question_number,
                    attempt + 1,
                    last_reason,
                )
                state.used_candidate_ids.add(candidate.candidate_id)
                continue

            validation = validate_generated_question(payload, candidate, evidence_content)
            if not validation.is_valid:
                last_reason = validation.reason
                logger.info(
                    "문항 %d 재시도 %d: 검증 실패 — %s",
                    question_number,
                    attempt + 1,
                    validation.reason,
                )
                state.used_candidate_ids.add(candidate.candidate_id)
                continue

            stem_emb, concept_emb = await cls._embed_for_dedup(payload, candidate)
            is_dup, dup_reason = is_duplicate_question(
                payload,
                candidate,
                state.generated_questions,
                stem_embedding=stem_emb,
                concept_embedding=concept_emb,
            )
            if is_dup:
                last_reason = dup_reason
                logger.info(
                    "문항 %d 재시도 %d: 중복 감지 — %s",
                    question_number,
                    attempt + 1,
                    dup_reason,
                )
                state.used_candidate_ids.add(candidate.candidate_id)
                continue

            for chunk in selected_chunks:
                key = str(chunk.chunk_id)
                state.chunk_usage_count[key] = state.chunk_usage_count.get(key, 0) + 1
            state.used_candidate_ids.add(candidate.candidate_id)

            record = GeneratedQuestionRecord(
                stem=payload.stem,
                answer=payload.answer,
                concepts=payload.concepts or [candidate.concept],
                stem_embedding=stem_emb,
                concept_embeddings=[concept_emb] if concept_emb else None,
            )
            state.generated_questions.append(record)

            logger.info(
                "문항 %d 생성 성공: concept=%s chunks=%s retries=%d",
                question_number,
                candidate.concept[:50],
                [str(c.chunk_id) for c in selected_chunks],
                attempt,
            )
            return payload, candidate, selected_chunks

        logger.warning(
            "문항 %d: %d회 재시도 후 실패 — %s",
            question_number,
            max_retries,
            last_reason,
        )
        return None

    @classmethod
    async def run_job(cls, db: AsyncSession, job: ExamGenerationJob) -> uuid.UUID:
        """RAG → 정답 후보 추출 → 후보별 생성·검증 → DB 저장."""
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
        all_chunks = await cls.retrieve_candidate_chunks(db, job.user_id, request)
        if not all_chunks:
            raise RuntimeError("RAG 검색 결과가 없습니다. 문서 인덱싱을 확인하세요.")

        logger.info("Job %s: RAG chunk %d개", job_id, len(all_chunks))
        chunk_map = cls._chunk_map(all_chunks)

        candidate_count = cls._candidate_count(request)
        await JobService.update_progress_by_id(
            job_id, "GENERATING", 15, "정답 후보 추출 중..."
        )
        raw_candidates = await cls.extract_answer_candidates(
            all_chunks, request, candidate_count
        )
        candidates = deduplicate_candidates(raw_candidates)
        logger.info(
            "Job %s: 후보 추출 %d개 → 중복 제거 후 %d개",
            job_id,
            len(raw_candidates),
            len(candidates),
        )
        if not candidates:
            raise RuntimeError("출제 가능한 정답 후보를 추출하지 못했습니다.")

        title = request.title or f"생성 문제집 {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
        exam = GeneratedExam(
            job_id=job.id,
            user_id=job.user_id,
            title=title,
            question_count=request.question_count,
        )
        db.add(exam)
        await db.flush()

        state = _JobGenerationState()
        saved_count = 0

        for i in range(request.question_count):
            qtype = cls._pick_question_type(request, i)
            pct = 20 + int((i / request.question_count) * 65)
            await JobService.update_progress_by_id(
                job_id,
                "GENERATING",
                pct,
                f"문제 {i + 1}/{request.question_count} 생성 중...",
            )

            result = await cls._try_generate_question(
                request,
                all_chunks,
                chunk_map,
                candidates,
                state,
                i + 1,
                qtype,
                style_profile,
            )
            if result is None:
                continue

            payload, candidate, selected_chunks = result
            saved_count += 1
            source_ids = [str(c.chunk_id) for c in selected_chunks]

            question = GeneratedQuestion(
                exam_id=exam.id,
                number=saved_count,
                question_type=payload.question_type,
                difficulty=payload.difficulty,
                bloom_level=payload.bloom_level or candidate.bloom_level,
                stem=payload.stem,
                choices=payload.choices,
                answer=payload.answer,
                explanation=payload.explanation,
                source_chunk_ids=source_ids,
            )
            db.add(question)
            await db.flush()
            concepts = payload.concepts if payload.concepts else [candidate.concept]
            for concept in concepts[:5]:
                db.add(QuestionConcept(question_id=question.id, concept=str(concept)[:200]))

        exam.question_count = saved_count
        if saved_count == 0:
            raise RuntimeError("생성에 성공한 문항이 없습니다.")
        if saved_count < request.question_count:
            logger.warning(
                "Job %s: 요청 %d문항 중 %d문항만 생성 (후보/중복/검증 실패)",
                job_id,
                request.question_count,
                saved_count,
            )

        logger.info("Job %s: 최종 생성 성공 %d문항", job_id, saved_count)
        await JobService.update_progress_by_id(job_id, "FINALIZING", 92, "문제집 저장 중...")
        await db.commit()
        return exam.id
