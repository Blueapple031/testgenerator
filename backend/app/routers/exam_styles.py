import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exam_style import ExamStyleAnalyzeRequest, ExamStyleProfileResponse
from app.services.exam_style_service import ExamStyleService

router = APIRouter()


@router.post(
    "/analyze",
    response_model=ExamStyleProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_exam_style(
    request: ExamStyleAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """족보 문서를 LLM으로 분석해 출제 스타일 프로필을 생성·갱신한다."""
    return await ExamStyleService.analyze(db, user.id, request)


@router.get("", response_model=list[ExamStyleProfileResponse])
async def list_exam_styles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """내 출제 스타일 프로필 목록"""
    return await ExamStyleService.list_profiles(db, user.id)


@router.get("/{profile_id}", response_model=ExamStyleProfileResponse)
async def get_exam_style(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """스타일 프로필 상세 조회"""
    return await ExamStyleService.get_profile(db, user.id, profile_id)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam_style(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """스타일 프로필 삭제"""
    await ExamStyleService.delete_profile(db, user.id, profile_id)
