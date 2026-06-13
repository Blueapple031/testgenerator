import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PilotAccountCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=100)
    token_quota: int | None = Field(default=None, ge=0)
    is_active: bool = True


class PilotAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    token_quota: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    reset_tokens_used: bool = False


class PilotAccountResponse(BaseModel):
    id: uuid.UUID
    code: str
    display_name: str
    token_quota: int | None
    tokens_used: int
    tokens_remaining: int | None
    is_active: bool
    created_at: datetime


class PilotSyncResponse(BaseModel):
    created: int
    updated: int
    deactivated: int
    accounts: list[PilotAccountResponse]
