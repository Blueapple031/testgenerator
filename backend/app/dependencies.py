"""공통 FastAPI 의존성.

Phase 1 단계에서는 실제 인증(세션/JWT)을 아직 구현하지 않으므로,
모든 데이터 격리의 기준이 되는 user_id 구조만 먼저 확보한다.
개발용 고정 사용자를 get-or-create 하여 반환하며,
추후 auth 라우터 구현 시 이 의존성을 실제 세션/JWT 검증으로 교체한다.
"""

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_USER_EMAIL = "dev@dontdelay.local"


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=DEV_USER_ID,
            email=DEV_USER_EMAIL,
            hashed_password="!dev-no-login",
            display_name="개발 사용자",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
