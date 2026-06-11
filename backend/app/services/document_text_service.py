"""PDF → 전체 텍스트 추출 (FULL_CONTEXT 벤치마크용).

인덱싱·chunk·embedding 없이 MinIO PDF를 PyMuPDF(+OCR/Vision)로 읽어
프롬프트에 넣을 단일 문자열을 만든다.
"""

import asyncio
import functools
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra import minio_client
from app.models.document import StudyDocument
from app.services.extraction_pipeline import enrich_pages
from app.services.extraction_service import ExtractionService, PageText

logger = logging.getLogger(__name__)


class DocumentTextService:
    @classmethod
    async def load_documents(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        *,
        require_indexed: bool,
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
        if require_indexed:
            not_ready = [d.filename for d in documents if d.status != "READY"]
            if not_ready:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"인덱싱이 완료되지 않은 문서: {', '.join(not_ready)}",
                )
        else:
            blocked = [d.filename for d in documents if d.status == "FAILED"]
            if blocked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"처리 실패 문서는 사용할 수 없습니다: {', '.join(blocked)}",
                )
        return documents

    @classmethod
    async def extract_document_text(
        cls,
        pdf_bytes: bytes,
        *,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> tuple[str, int, int]:
        """PDF 바이트 → (본문, 사용 페이지 수, 추출 문자 수)."""
        loop = asyncio.get_running_loop()
        pages, _page_count = await loop.run_in_executor(
            None, functools.partial(ExtractionService.extract_pages, pdf_bytes)
        )
        pages, stats = await enrich_pages(pdf_bytes, pages)
        logger.info(
            "PDF 텍스트 추출 — OCR %d, Vision %d / %d페이지",
            stats.ocr_pages,
            stats.vision_pages,
            stats.total_pages,
        )

        if page_start is not None or page_end is not None:
            start = page_start or 1
            end = page_end or max(p.page_number for p in pages)
            pages = [p for p in pages if start <= p.page_number <= end]

        parts: list[str] = []
        for page in pages:
            text = page.text.strip()
            if text:
                parts.append(f"[p.{page.page_number}]\n{text}")

        body = "\n\n".join(parts)
        return body, len(pages), len(body)

    @classmethod
    def truncate_for_context(cls, text: str, max_chars: int) -> tuple[str, bool]:
        if len(text) <= max_chars:
            return text, False
        truncated = text[:max_chars]
        cut_at = truncated.rfind("\n\n")
        if cut_at > max_chars * 0.7:
            truncated = truncated[:cut_at]
        return truncated + "\n\n[... 본문이 토큰 한도로 잘렸습니다 ...]", True

    @classmethod
    async def build_combined_context(
        cls,
        documents: list[StudyDocument],
        *,
        page_start: int | None = None,
        page_end: int | None = None,
        max_chars: int | None = None,
    ) -> tuple[str, bool]:
        """여러 PDF 본문을 하나의 프롬프트 문자열로 합친다."""
        limit = max_chars or settings.EXAM_GEN_FULL_CONTEXT_MAX_CHARS
        sections: list[str] = []
        for document in documents:
            pdf_bytes = await minio_client.download_file(document.minio_key)
            body, page_count, char_count = await cls.extract_document_text(
                pdf_bytes,
                page_start=page_start,
                page_end=page_end,
            )
            if not body.strip():
                raise ValueError(f"텍스트를 추출하지 못했습니다: {document.filename}")
            sections.append(
                f"=== {document.filename} ({page_count}페이지, {char_count}자) ===\n{body}"
            )
        combined = "\n\n".join(sections)
        return cls.truncate_for_context(combined, limit)
