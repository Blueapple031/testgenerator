import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exam import ExamListItem, ExamResponse
from app.services.exam_service import ExamService

router = APIRouter()


@router.get("", response_model=list[ExamListItem])
async def list_exams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """생성된 시험 목록"""
    return await ExamService.list_exams(db, user.id)


@router.post("/demo", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_demo_exam(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Phase 5 미리보기·인쇄 확인용 데모 시험 생성"""
    return await ExamService.create_demo_exam(db, user.id)


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """전체 시험 JSON 조회 (웹 렌더링용)"""
    return await ExamService.get_exam(db, user.id, exam_id)


@router.get("/{exam_id}/export")
async def export_exam_pdf(exam_id: uuid.UUID):
    """선택적 PDF보내기 (고도화). MVP는 웹 렌더링 + 브라우저 인쇄 사용."""
    raise NotImplementedError


@router.patch("/{exam_id}/questions/{question_id}")
async def update_question(exam_id: uuid.UUID, question_id: uuid.UUID):
    """개별 문제 수정 — Phase 6에서 구현"""
    raise NotImplementedError


@router.post("/{exam_id}/questions/{question_id}/regenerate")
async def regenerate_question(exam_id: uuid.UUID, question_id: uuid.UUID):
    """개별 문제 재생성 — Phase 6에서 구현"""
    raise NotImplementedError


@router.delete("/{exam_id}/questions/{question_id}")
async def delete_question(exam_id: uuid.UUID, question_id: uuid.UUID):
    """문제 삭제 — Phase 6에서 구현"""
    raise NotImplementedError


@router.post("/{exam_id}/export")
async def trigger_exam_export(exam_id: uuid.UUID):
    """편집 후 PDF보내기 재생성 (고도화, HTML 기반 export)"""
    raise NotImplementedError
