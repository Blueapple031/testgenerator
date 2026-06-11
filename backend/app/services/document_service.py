"""PDF 업로드, 문서 조회 비즈니스 로직."""

import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra import minio_client
from app.models.document import StudyDocument

ALLOWED_DOCUMENT_TYPES = {"lecture", "past_exam"}
PDF_CONTENT_TYPE = "application/pdf"


class DocumentService:
    @staticmethod
    def _validate(document_type: str, filename: str, content_type: str | None, size: int) -> None:
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"document_type은 {ALLOWED_DOCUMENT_TYPES} 중 하나여야 합니다.",
            )
        if not filename.lower().endswith(".pdf") or (content_type and content_type != PDF_CONTENT_TYPE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF 파일만 업로드할 수 있습니다.",
            )
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 파일은 업로드할 수 없습니다.",
            )
        if size > settings.EXAM_MAX_UPLOAD_BYTES:
            max_mb = settings.EXAM_MAX_UPLOAD_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"파일 크기는 최대 {max_mb}MB까지 허용됩니다.",
            )

    @classmethod
    async def upload(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        file: UploadFile,
        document_type: str,
        workspace_id: uuid.UUID | None = None,
    ) -> StudyDocument:
        data = await file.read()
        cls._validate(document_type, file.filename or "", file.content_type, len(data))

        document_id = uuid.uuid4()
        minio_key = f"{user_id}/{document_type}/{document_id}.pdf"
        await minio_client.upload_file(minio_key, data, PDF_CONTENT_TYPE)

        document = StudyDocument(
            id=document_id,
            user_id=user_id,
            workspace_id=workspace_id,
            document_type=document_type,
            filename=file.filename or f"{document_id}.pdf",
            minio_key=minio_key,
            status="UPLOADED",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def list(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_type: str | None = None,
    ) -> list[StudyDocument]:
        stmt = select(StudyDocument).where(StudyDocument.user_id == user_id)
        if document_type is not None:
            stmt = stmt.where(StudyDocument.document_type == document_type)
        stmt = stmt.order_by(StudyDocument.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> StudyDocument:
        stmt = select(StudyDocument).where(
            StudyDocument.id == document_id,
            StudyDocument.user_id == user_id,
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문서를 찾을 수 없습니다.",
            )
        return document
