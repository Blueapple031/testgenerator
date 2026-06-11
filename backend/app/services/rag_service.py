"""pgvector cosine 유사도 기반 RAG 검색.

요청 텍스트를 embedding한 뒤 document_chunk.embedding과 비교해
관련도가 높은 chunk topK를 반환한다. Phase 4 문제 생성에서도 재사용한다.
"""

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra.embedding_client import get_embedding
from app.models.document import DocumentChunk, StudyDocument


@dataclass
class ChunkHit:
    chunk_id: uuid.UUID
    chunk_index: int
    content: str
    page_start: int | None
    page_end: int | None
    extraction_method: str
    similarity: float


class RagService:
    @staticmethod
    def _clamp_top_k(top_k: int) -> int:
        return min(max(top_k, 1), settings.RAG_MAX_TOP_K)

    @classmethod
    async def search(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        query: str,
        top_k: int | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> list[ChunkHit]:
        """여러 문서 범위에서 query와 의미적으로 가까운 chunk를 검색한다."""
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="검색 대상 문서가 없습니다.",
            )
        if page_start is not None and page_end is not None and page_start > page_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page_start는 page_end보다 클 수 없습니다.",
            )

        limit = cls._clamp_top_k(top_k or settings.RAG_DEFAULT_TOP_K)
        query_vector = await get_embedding(query.strip())
        distance = DocumentChunk.embedding.cosine_distance(query_vector)

        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.page_start,
                DocumentChunk.page_end,
                DocumentChunk.extraction_method,
                distance.label("distance"),
            )
            .join(StudyDocument, DocumentChunk.document_id == StudyDocument.id)
            .where(
                StudyDocument.user_id == user_id,
                DocumentChunk.document_id.in_(document_ids),
                DocumentChunk.embedding.isnot(None),
            )
        )

        if page_start is not None:
            stmt = stmt.where(DocumentChunk.page_start >= page_start)
        if page_end is not None:
            stmt = stmt.where(DocumentChunk.page_start <= page_end)

        stmt = stmt.order_by(distance).limit(limit)
        result = await db.execute(stmt)

        hits: list[ChunkHit] = []
        for row in result.all():
            # pgvector cosine distance: 0에 가까울수록 유사. similarity = 1 - distance.
            similarity = 1.0 - float(row.distance)
            hits.append(
                ChunkHit(
                    chunk_id=row.id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    page_start=row.page_start,
                    page_end=row.page_end,
                    extraction_method=row.extraction_method,
                    similarity=round(similarity, 4),
                )
            )
        return hits
