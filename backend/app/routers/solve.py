import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.feedback import ExamFeedbackListResponse, QuestionFeedbackRequest, QuestionFeedbackResponse
from app.services.question_feedback_service import QuestionFeedbackService

router = APIRouter()


@router.post("/{exam_id}/answers")
async def submit_answers(exam_id: str):
    """풀이 결과 제출 (풀이 시간 포함)"""
    raise NotImplementedError


@router.post("/{exam_id}/interactions")
async def log_interactions(exam_id: str):
    """풀이 이벤트 로그 저장 (시작, 제출, 힌트, 답 변경, 이탈)"""
    raise NotImplementedError


@router.get("/{exam_id}/feedback", response_model=ExamFeedbackListResponse)
async def list_exam_feedback(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """시험 내 현재 사용자의 문항 평가 목록"""
    feedback = await QuestionFeedbackService.list_exam_feedback(db, user.id, exam_id)
    return ExamFeedbackListResponse(feedback=feedback)


@router.put(
    "/{exam_id}/questions/{question_id}/feedback",
    response_model=QuestionFeedbackResponse,
)
async def upsert_question_feedback(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: QuestionFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """문항 평가 저장 (좋아요/별로, 별로 시 사유·코멘트)"""
    return await QuestionFeedbackService.upsert_feedback(
        db, user.id, exam_id, question_id, payload
    )
