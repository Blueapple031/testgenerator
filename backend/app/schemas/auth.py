import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class UserMeResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    tokens_used: int
    token_quota: int | None
    tokens_remaining: int | None
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    user: UserMeResponse
