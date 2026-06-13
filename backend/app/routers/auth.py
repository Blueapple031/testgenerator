from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserMeResponse
from app.services.auth_service import create_access_token
from app.services.pilot_account_service import PilotAccountService, user_to_me

router = APIRouter()


def _set_auth_cookie(response: Response, token: str) -> None:
    max_age = settings.JWT_EXPIRE_HOURS * 3600
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """접속 코드로 로그인하고 JWT 쿠키를 발급한다."""
    if not settings.PILOT_AUTH_ENABLED:
        from app.dependencies import _get_dev_user

        user = await _get_dev_user(db)
    else:
        user = await PilotAccountService.authenticate(db, body.code)

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return LoginResponse(user=user_to_me(user))


@router.get("/me", response_model=UserMeResponse)
async def me(user: User = Depends(get_current_user)):
    """현재 로그인 사용자 정보 및 토큰 사용량."""
    return user_to_me(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """로그아웃 (쿠키 삭제)."""
    _clear_auth_cookie(response)
