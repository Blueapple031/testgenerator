"""파일럿 인증 및 토큰 한도 테스트."""

import uuid

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.pilot_account_service import PilotAccountService


def _pilot_user(
    *,
    code: str = "test-code",
    quota: int | None = 1000,
    used: int = 0,
    active: bool = True,
) -> User:
    return User(
        id=uuid.uuid4(),
        email="test-code@pilot.dontdelay.local",
        hashed_password="!pilot-invite-only",
        display_name="테스트",
        invite_code=code,
        token_quota=quota,
        tokens_used=used,
        is_active=active,
    )


@pytest.mark.asyncio
async def test_me_returns_user_info():
    user = _pilot_user(quota=500, used=100)

    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "테스트"
        assert data["tokens_used"] == 100
        assert data["token_quota"] == 500
        assert data["tokens_remaining"] == 400
    finally:
        app.dependency_overrides.clear()


def test_ensure_quota_available_blocks_when_exhausted():
    user = _pilot_user(quota=100, used=100)
    with pytest.raises(HTTPException) as exc:
        PilotAccountService.ensure_quota_available(user)
    assert exc.value.status_code == 403


def test_ensure_quota_available_allows_unlimited():
    user = _pilot_user(quota=None, used=999_999)
    PilotAccountService.ensure_quota_available(user)


def test_user_tokens_remaining():
    user = _pilot_user(quota=1000, used=250)
    assert user.tokens_remaining == 750

    unlimited = _pilot_user(quota=None, used=250)
    assert unlimited.tokens_remaining is None
