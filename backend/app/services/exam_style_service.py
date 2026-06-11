"""족보 분석 → 출제 스타일 프로필 생성."""

import asyncio
import functools
import json
import logging
import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra import minio_client
from app.infra.llm_client import openai_client
from app.infra.ocr_client import ocr_pages
from app.models.document import StudyDocument
from app.models.exam_style import ExamStyleProfile
from app.schemas.exam_style import (
    ExamStyleAnalyzeRequest,
    ExamStyleProfileResponse,
    StyleAnalysisPayload,
)
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)

ALLOWED_TYPE_KEYS = {
    "multiple_choice",
    "short_answer",
    "essay_short",
    "essay_long",
}
ALLOWED_BLOOM_KEYS = {
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
}


class ExamStyleService:
    @staticmethod
    async def _get_past_exam_document(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> StudyDocument:
        result = await db.execute(
            select(StudyDocument).where(
                StudyDocument.id == document_id,
                StudyDocument.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문서를 찾을 수 없습니다.",
            )
        if document.document_type != "past_exam":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="족보(past_exam) 문서만 출제 스타일 분석이 가능합니다.",
            )
        return document

    @classmethod
    async def _extract_text_from_pdf(cls, pdf_bytes: bytes) -> str:
        loop = asyncio.get_running_loop()
        pages, _ = await loop.run_in_executor(
            None, functools.partial(ExtractionService.extract_pages, pdf_bytes)
        )
        if settings.OCR_ENABLED and ExtractionService.needs_ocr(pages):
            pages, _ = await ocr_pages(pdf_bytes, pages)

        parts: list[str] = []
        for page in pages:
            text = page.text.strip()
            if text:
                parts.append(f"[p.{page.page_number}]\n{text}")
        return "\n\n".join(parts)

    @classmethod
    async def _resolve_exam_text(
        cls,
        document: StudyDocument,
        raw_text: str | None,
    ) -> str:
        if raw_text and raw_text.strip():
            return raw_text.strip()

        pdf_bytes = await minio_client.download_file(document.minio_key)
        text = await cls._extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="족보에서 텍스트를 추출하지 못했습니다. raw_text로 직접 입력해 주세요.",
            )
        return text

    @staticmethod
    def _truncate_text(text: str) -> str:
        limit = settings.EXAM_STYLE_MAX_TEXT_CHARS
        if len(text) <= limit:
            return text
        return text[:limit] + "\n\n[... 이하 생략 ...]"

    @staticmethod
    def _normalize_distribution(
        raw: dict[str, int],
        allowed_keys: set[str],
    ) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key, value in raw.items():
            if key in allowed_keys and isinstance(value, int) and value >= 0:
                normalized[key] = value
        return normalized

    @classmethod
    async def _analyze_with_llm(
        cls,
        exam_text: str,
        professor_name: str | None,
        subject: str | None,
    ) -> StyleAnalysisPayload:
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY가 설정되지 않았습니다.",
            )

        meta = []
        if professor_name:
            meta.append(f"교수명(사용자 입력): {professor_name}")
        if subject:
            meta.append(f"과목(사용자 입력): {subject}")
        meta_section = "\n".join(meta) if meta else "교수명·과목은 족보 내용에서 추정해 주세요."

        system_prompt = (
            "당신은 대학 시험 족보를 분석하는 출제 스타일 분석 전문가입니다. "
            "제공된 족보 텍스트만 근거로 JSON을 출력하세요."
        )
        user_prompt = f"""다음 족보를 분석해 출제 스타일 프로필을 만드세요.

[메타정보]
{meta_section}

[족보 텍스트]
{exam_text}

[출력 JSON 스키마]
{{
  "professor_name": "교수명 또는 null",
  "subject": "과목명 또는 null",
  "type_distribution": {{
    "multiple_choice": 0,
    "short_answer": 0,
    "essay_short": 0,
    "essay_long": 0
  }},
  "bloom_distribution": {{
    "remember": 0,
    "understand": 0,
    "apply": 0,
    "analyze": 0,
    "evaluate": 0,
    "create": 0
  }},
  "avg_questions_per_exam": 1,
  "common_concepts": ["개념1", "개념2"],
  "style_notes": "출제 패턴 요약 (지문 길이, 비교형 서술, 코드 분석 등)"
}}

type_distribution·bloom_distribution 값은 비율(%)이며 합이 각각 100에 가깝게 맞추세요."""

        response = await openai_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            payload = StyleAnalysisPayload.model_validate(data)
            payload.type_distribution = cls._normalize_distribution(
                payload.type_distribution, ALLOWED_TYPE_KEYS
            )
            payload.bloom_distribution = cls._normalize_distribution(
                payload.bloom_distribution, ALLOWED_BLOOM_KEYS
            )
            if professor_name:
                payload.professor_name = professor_name
            if subject:
                payload.subject = subject
            return payload
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("족보 분석 JSON 검증 실패: %s — raw=%s", exc, raw[:300])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"족보 분석 결과 검증 실패: {exc}",
            ) from exc

    @staticmethod
    def _to_response(
        profile: ExamStyleProfile,
        document_filename: str | None = None,
    ) -> ExamStyleProfileResponse:
        return ExamStyleProfileResponse(
            id=profile.id,
            document_id=profile.document_id,
            document_filename=document_filename,
            professor_name=profile.professor_name,
            subject=profile.subject,
            analyzed_exam_count=profile.analyzed_exam_count,
            type_distribution=profile.type_distribution,
            bloom_distribution=profile.bloom_distribution,
            avg_questions_per_exam=profile.avg_questions_per_exam,
            common_concepts=profile.common_concepts,
            style_notes=profile.style_notes,
            created_at=profile.created_at,
        )

    @classmethod
    async def analyze(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        request: ExamStyleAnalyzeRequest,
    ) -> ExamStyleProfileResponse:
        document = await cls._get_past_exam_document(db, user_id, request.document_id)
        exam_text = cls._truncate_text(
            await cls._resolve_exam_text(document, request.raw_text)
        )
        analysis = await cls._analyze_with_llm(
            exam_text, request.professor_name, request.subject
        )

        result = await db.execute(
            select(ExamStyleProfile).where(ExamStyleProfile.document_id == document.id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = ExamStyleProfile(
                user_id=user_id,
                document_id=document.id,
                analyzed_exam_count=1,
            )
            db.add(profile)
        else:
            profile.analyzed_exam_count += 1

        profile.professor_name = analysis.professor_name
        profile.subject = analysis.subject
        profile.type_distribution = analysis.type_distribution
        profile.bloom_distribution = analysis.bloom_distribution
        profile.avg_questions_per_exam = analysis.avg_questions_per_exam
        profile.common_concepts = analysis.common_concepts[:20]
        profile.style_notes = analysis.style_notes

        await db.commit()
        await db.refresh(profile)
        return cls._to_response(profile, document.filename)

    @classmethod
    async def list_profiles(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[ExamStyleProfileResponse]:
        stmt = (
            select(ExamStyleProfile, StudyDocument.filename)
            .join(StudyDocument, ExamStyleProfile.document_id == StudyDocument.id)
            .where(ExamStyleProfile.user_id == user_id)
            .order_by(ExamStyleProfile.created_at.desc())
        )
        result = await db.execute(stmt)
        return [
            cls._to_response(profile, filename)
            for profile, filename in result.all()
        ]

    @classmethod
    async def get_profile(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> ExamStyleProfileResponse:
        stmt = (
            select(ExamStyleProfile, StudyDocument.filename)
            .join(StudyDocument, ExamStyleProfile.document_id == StudyDocument.id)
            .where(
                ExamStyleProfile.id == profile_id,
                ExamStyleProfile.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="출제 스타일 프로필을 찾을 수 없습니다.",
            )
        profile, filename = row
        return cls._to_response(profile, filename)

    @classmethod
    async def delete_profile(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> None:
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
        await db.delete(profile)
        await db.commit()
