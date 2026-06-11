"""비동기 문서 인덱싱 파이프라인.

다운로드(MinIO) → 텍스트 추출(PyMuPDF) → OCR/Vision 보강 (EXTRACTION_PIPELINE)
→ chunking → embedding → pgvector 저장.

문서 상태 머신: UPLOADED → EXTRACTING → INDEXING → READY (실패 시 FAILED)
"""

import asyncio
import functools
import logging
import uuid

from sqlalchemy import delete

from app.config import settings
from app.database import async_session
from app.infra import minio_client
from app.models.document import DocumentChunk, StudyDocument
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.extraction_pipeline import enrich_pages
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)


async def index_document(document_id: uuid.UUID) -> None:
    """단일 문서를 인덱싱한다. 백그라운드 태스크로 호출되며 예외를 전파하지 않는다."""
    async with async_session() as db:
        document = await db.get(StudyDocument, document_id)
        if document is None:
            logger.warning("인덱싱 대상 문서를 찾을 수 없음: %s", document_id)
            return

        try:
            await _set_status(db, document, "EXTRACTING")

            pdf_bytes = await minio_client.download_file(document.minio_key)

            loop = asyncio.get_running_loop()
            pages, page_count = await loop.run_in_executor(
                None, functools.partial(ExtractionService.extract_pages, pdf_bytes)
            )
            document.page_count = page_count

            pages, enrich_stats = await enrich_pages(pdf_bytes, pages)
            logger.info(
                "추출 파이프라인 [%s] 완료 — OCR %d페이지, Vision %d페이지 / 전체 %d페이지",
                enrich_stats.pipeline,
                enrich_stats.ocr_pages,
                enrich_stats.vision_pages,
                enrich_stats.total_pages,
            )

            await _set_status(db, document, "INDEXING")

            chunks = ChunkService.chunk_pages(
                pages, settings.EXAM_CHUNK_SIZE, settings.EXAM_CHUNK_OVERLAP
            )

            # 재인덱싱을 대비해 기존 chunk를 제거한 뒤 새로 저장한다(idempotent).
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )

            if chunks:
                embeddings = await EmbeddingService.embed_texts([c.content for c in chunks])
                for chunk, embedding in zip(chunks, embeddings):
                    db.add(
                        DocumentChunk(
                            document_id=document_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            extraction_method=chunk.source,
                            embedding=embedding,
                        )
                    )

            await _set_status(db, document, "READY")
            logger.info("문서 인덱싱 완료: %s (chunks=%d)", document_id, len(chunks))
        except Exception:
            logger.exception("문서 인덱싱 실패: %s", document_id)
            await _set_status(db, document, "FAILED")


async def _set_status(db, document: StudyDocument, status: str) -> None:
    document.status = status
    await db.commit()
