import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import verify_admin_key
from app.schemas.pilot import (
    PilotAccountCreate,
    PilotAccountResponse,
    PilotAccountUpdate,
    PilotSyncResponse,
)
from app.services.pilot_account_service import PilotAccountService

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/accounts", response_model=list[PilotAccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """파일럿 계정 목록 (코드, 이름, 토큰 사용량)."""
    return await PilotAccountService.list_accounts(db)


@router.post("/accounts", response_model=PilotAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(body: PilotAccountCreate, db: AsyncSession = Depends(get_db)):
    """새 파일럿 계정 생성."""
    return await PilotAccountService.create_account(db, body)


@router.patch("/accounts/{account_id}", response_model=PilotAccountResponse)
async def update_account(
    account_id: uuid.UUID,
    body: PilotAccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """파일럿 계정 수정 (이름, 한도, 활성화, 사용량 초기화)."""
    return await PilotAccountService.update_account(db, account_id, body)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """파일럿 계정 비활성화."""
    await PilotAccountService.deactivate_account(db, account_id)


@router.post("/sync", response_model=PilotSyncResponse)
async def sync_accounts(db: AsyncSession = Depends(get_db)):
    """pilot_accounts.yaml 파일과 DB를 동기화."""
    path = Path(settings.PILOT_ACCOUNTS_PATH)
    return await PilotAccountService.sync_from_yaml(db, path)
