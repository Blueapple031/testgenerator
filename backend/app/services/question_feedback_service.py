"""문항 품질 피드백 저장·조회."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import QuestionFeedback
from app.models.exam import GeneratedExam, GeneratedQuestion
from app.schemas.feedback import QuestionFeedbackRequest, QuestionFeedbackResponse


class QuestionFeedbackService:
    @staticmethod
    async def _get_owned_exam(
        db: AsyncSession,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> GeneratedExam:
        result = await db.execute(
            select(GeneratedExam).where(
                GeneratedExam.id == exam_id,
                GeneratedExam.user_id == user_id,
            )
        )
        exam = result.scalar_one_or_none()
        if exam is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시험을 찾을 수 없습니다.",
            )
        return exam

    @staticmethod
    async def _get_question_in_exam(
        db: AsyncSession,
        exam_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> GeneratedQuestion:
        result = await db.execute(
            select(GeneratedQuestion).where(
                GeneratedQuestion.id == question_id,
                GeneratedQuestion.exam_id == exam_id,
            )
        )
        question = result.scalar_one_or_none()
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문항을 찾을 수 없습니다.",
            )
        return question

    @classmethod
    async def upsert_feedback(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
        question_id: uuid.UUID,
        payload: QuestionFeedbackRequest,
    ) -> QuestionFeedbackResponse:
        await cls._get_owned_exam(db, user_id, exam_id)
        await cls._get_question_in_exam(db, exam_id, question_id)

        result = await db.execute(
            select(QuestionFeedback).where(
                QuestionFeedback.user_id == user_id,
                QuestionFeedback.question_id == question_id,
            )
        )
        feedback = result.scalar_one_or_none()

        if feedback is None:
            feedback = QuestionFeedback(
                user_id=user_id,
                exam_id=exam_id,
                question_id=question_id,
                rating=payload.rating,
                reason_tags=payload.reason_tags or None,
                comment=payload.comment,
            )
            db.add(feedback)
        else:
            feedback.rating = payload.rating
            feedback.reason_tags = payload.reason_tags or None
            feedback.comment = payload.comment
            feedback.exam_id = exam_id

        await db.commit()
        await db.refresh(feedback)
        return QuestionFeedbackResponse.model_validate(feedback)

    @classmethod
    async def list_exam_feedback(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> list[QuestionFeedbackResponse]:
        await cls._get_owned_exam(db, user_id, exam_id)

        result = await db.execute(
            select(QuestionFeedback).where(
                QuestionFeedback.user_id == user_id,
                QuestionFeedback.exam_id == exam_id,
            )
        )
        rows = result.scalars().all()
        return [QuestionFeedbackResponse.model_validate(row) for row in rows]
