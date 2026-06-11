from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
