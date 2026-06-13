"""파일럿 계정 관리 및 토큰 사용량 한도."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import yaml
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import UserMeResponse
from app.schemas.pilot import (
    PilotAccountCreate,
    PilotAccountResponse,
    PilotAccountUpdate,
    PilotSyncResponse,
)

logger = logging.getLogger(__name__)

PILOT_PASSWORD_PLACEHOLDER = "!pilot-invite-only"


def normalize_code(code: str) -> str:
    return code.strip()


def pilot_email_for_code(code: str) -> str:
    normalized = normalize_code(code).lower()
    return f"{normalized}@pilot.dontdelay.local"


def user_to_me(user: User) -> UserMeResponse:
    return UserMeResponse(
        id=user.id,
        display_name=user.display_name,
        tokens_used=user.tokens_used,
        token_quota=user.token_quota,
        tokens_remaining=user.tokens_remaining,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def user_to_pilot_account(user: User) -> PilotAccountResponse:
    if not user.invite_code:
        raise ValueError("invite_code가 없는 사용자입니다.")
    return PilotAccountResponse(
        id=user.id,
        code=user.invite_code,
        display_name=user.display_name,
        token_quota=user.token_quota,
        tokens_used=user.tokens_used,
        tokens_remaining=user.tokens_remaining,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class PilotAccountService:
    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> User | None:
        normalized = normalize_code(code)
        result = await db.execute(
            select(User).where(func.lower(User.invite_code) == normalized.lower())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate(db: AsyncSession, code: str) -> User:
        user = await PilotAccountService.get_by_code(db, code)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 접속 코드입니다.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
            )
        return user

    @staticmethod
    async def list_accounts(db: AsyncSession) -> list[PilotAccountResponse]:
        result = await db.execute(
            select(User)
            .where(User.invite_code.is_not(None))
            .order_by(User.created_at.asc())
        )
        return [user_to_pilot_account(u) for u in result.scalars().all()]

    @staticmethod
    async def create_account(db: AsyncSession, data: PilotAccountCreate) -> PilotAccountResponse:
        code = normalize_code(data.code)
        existing = await PilotAccountService.get_by_code(db, code)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 접속 코드입니다.",
            )

        user = User(
            email=pilot_email_for_code(code),
            hashed_password=PILOT_PASSWORD_PLACEHOLDER,
            display_name=data.display_name.strip(),
            invite_code=code,
            token_quota=data.token_quota,
            tokens_used=0,
            is_active=data.is_active,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user_to_pilot_account(user)

    @staticmethod
    async def update_account(
        db: AsyncSession,
        account_id: uuid.UUID,
        data: PilotAccountUpdate,
    ) -> PilotAccountResponse:
        user = await db.get(User, account_id)
        if user is None or user.invite_code is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계정을 찾을 수 없습니다.")

        if data.display_name is not None:
            user.display_name = data.display_name.strip()
        if data.token_quota is not None:
            user.token_quota = data.token_quota
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.reset_tokens_used:
            user.tokens_used = 0

        await db.commit()
        await db.refresh(user)
        return user_to_pilot_account(user)

    @staticmethod
    async def deactivate_account(db: AsyncSession, account_id: uuid.UUID) -> None:
        user = await db.get(User, account_id)
        if user is None or user.invite_code is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="계정을 찾을 수 없습니다.")
        user.is_active = False
        await db.commit()

    @staticmethod
    def ensure_quota_available(user: User) -> None:
        if user.token_quota is None:
            return
        if user.tokens_used >= user.token_quota:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"토큰 사용 한도({user.token_quota:,})에 도달했습니다. "
                    "관리자에게 한도 증설을 요청하세요."
                ),
            )

    @staticmethod
    async def record_token_usage(db: AsyncSession, user_id: uuid.UUID, tokens: int) -> None:
        if tokens <= 0:
            return
        user = await db.get(User, user_id)
        if user is None:
            return
        user.tokens_used += tokens
        await db.commit()

    @staticmethod
    async def sync_from_yaml(db: AsyncSession, path: Path) -> PilotSyncResponse:
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"파일럿 계정 설정 파일을 찾을 수 없습니다: {path}",
            )

        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        entries = raw.get("accounts") or []
        if not isinstance(entries, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="accounts 항목은 리스트여야 합니다.",
            )

        created = 0
        updated = 0
        seen_codes: set[str] = set()

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            code = normalize_code(str(entry.get("code", "")))
            display_name = str(entry.get("display_name", "")).strip()
            if not code or not display_name:
                continue

            token_quota = entry.get("token_quota")
            if token_quota is not None:
                token_quota = int(token_quota)
            is_active = bool(entry.get("is_active", True))
            seen_codes.add(code.lower())

            user = await PilotAccountService.get_by_code(db, code)
            if user is None:
                await PilotAccountService.create_account(
                    db,
                    PilotAccountCreate(
                        code=code,
                        display_name=display_name,
                        token_quota=token_quota,
                        is_active=is_active,
                    ),
                )
                created += 1
            else:
                user.display_name = display_name
                user.token_quota = token_quota
                user.is_active = is_active
                await db.commit()
                updated += 1

        deactivated = 0
        result = await db.execute(select(User).where(User.invite_code.is_not(None)))
        for user in result.scalars().all():
            if user.invite_code and user.invite_code.lower() not in seen_codes and user.is_active:
                user.is_active = False
                deactivated += 1
        if deactivated:
            await db.commit()

        accounts = await PilotAccountService.list_accounts(db)
        logger.info("파일럿 계정 동기화: created=%s updated=%s deactivated=%s", created, updated, deactivated)
        return PilotSyncResponse(
            created=created,
            updated=updated,
            deactivated=deactivated,
            accounts=accounts,
        )
