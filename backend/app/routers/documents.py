import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.infra import minio_client
from app.models.user import User
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.workers.document_indexing import index_document

router = APIRouter()


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    workspace_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PDF 업로드 (type: lecture / past_exam) 후 인덱싱을 백그라운드로 시작한다."""
    document = await DocumentService.upload(
        db, user.id, file, document_type, workspace_id
    )
    background_tasks.add_task(index_document, document.id)
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    document_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """문서 목록 (강의자료·족보 필터)"""
    return await DocumentService.list(db, user.id, document_type)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """문서 처리 상태 조회"""
    return await DocumentService.get(db, user.id, document_id)


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """원본 PDF presigned 다운로드 URL 발급"""
    document = await DocumentService.get(db, user.id, document_id)
    url = await minio_client.get_presigned_url(document.minio_key)
    return DocumentDownloadResponse(url=url)


@router.post("/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """문서 인덱싱을 다시 실행한다 (추출 → chunking → embedding → pgvector)."""
    document = await DocumentService.get(db, user.id, document_id)
    background_tasks.add_task(index_document, document.id)
    return {"document_id": str(document.id), "status": "reindexing"}


@router.get("/{document_id}/toc")
async def get_document_toc(document_id: uuid.UUID):
    """PDF 목차 조회 (시험 범위 선택용) — Phase 8에서 구현"""
    raise NotImplementedError


@router.post("/{document_id}/search")
async def search_document(document_id: uuid.UUID):
    """RAG 검색 테스트 — Phase 3에서 구현"""
    raise NotImplementedError
