from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    document_type: str
    status: str


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    document_type: str
    status: str
    page_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TocEntry(BaseModel):
    level: int
    title: str
    page_number: int


class DocumentDownloadResponse(BaseModel):
    url: str


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=30)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)


class ChunkSearchResult(BaseModel):
    chunk_id: UUID
    chunk_index: int
    content: str
    page_start: int | None
    page_end: int | None
    extraction_method: str
    similarity: float


class DocumentSearchResponse(BaseModel):
    query: str
    document_id: UUID
    top_k: int
    results: list[ChunkSearchResult]
