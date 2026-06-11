"""시험 생성 Job 등록·조회."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import ExamGenerationJob, GeneratedExam
from app.schemas.exam import ExamGenerationRequest, JobStatusResponse


class JobService:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        request: ExamGenerationRequest,
    ) -> ExamGenerationJob:
        job = ExamGenerationJob(
            user_id=user_id,
            workspace_id=request.workspace_id,
            status="PENDING",
            progress=0,
            message="대기 중",
            options=request.model_dump(mode="json"),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def get(
        db: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> JobStatusResponse:
        result = await db.execute(
            select(ExamGenerationJob).where(
                ExamGenerationJob.id == job_id,
                ExamGenerationJob.user_id == user_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job을 찾을 수 없습니다.",
            )

        exam_id = await JobService._exam_id_for_job(db, job_id)
        return JobStatusResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            message=job.message,
            exam_id=exam_id,
            created_at=job.created_at,
        )

    @staticmethod
    async def get_job_row(
        db: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ExamGenerationJob:
        result = await db.execute(
            select(ExamGenerationJob).where(
                ExamGenerationJob.id == job_id,
                ExamGenerationJob.user_id == user_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job을 찾을 수 없습니다.",
            )
        return job

    @staticmethod
    async def _exam_id_for_job(db: AsyncSession, job_id: uuid.UUID) -> uuid.UUID | None:
        result = await db.execute(
            select(GeneratedExam.id).where(GeneratedExam.job_id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        job: ExamGenerationJob,
        status: str,
        progress: int,
        message: str | None,
        *,
        completed: bool = False,
    ) -> None:
        job.status = status
        job.progress = min(max(progress, 0), 100)
        job.message = message
        if completed:
            job.completed_at = datetime.now(UTC)
        await db.commit()

    @staticmethod
    async def update_progress_by_id(
        job_id: uuid.UUID,
        status: str,
        progress: int,
        message: str | None,
        *,
        completed: bool = False,
    ) -> None:
        """별도 세션으로 Job 진행률만 갱신 (시험 생성 트랜잭션과 분리)."""
        from app.database import async_session

        async with async_session() as db:
            job = await db.get(ExamGenerationJob, job_id)
            if job is None:
                return
            job.status = status
            job.progress = min(max(progress, 0), 100)
            job.message = message
            if completed:
                job.completed_at = datetime.now(UTC)
            await db.commit()
