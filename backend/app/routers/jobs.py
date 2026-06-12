import asyncio
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exam import ExamGenerationRequest, JobCreateResponse, JobStatusResponse, JobStreamEvent
from app.services.exam_generation_service import ExamGenerationService
from app.services.job_service import JobService
from app.workers.exam_generation import generate_exam

router = APIRouter()

SSE_POLL_INTERVAL_SEC = 1.0
SSE_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: ExamGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """문제집 생성 Job 등록 후 백그라운드에서 LLM 생성을 시작한다."""
    if request.question_count > settings.EXAM_MAX_QUESTION_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"문항 수는 최대 {settings.EXAM_MAX_QUESTION_COUNT}개입니다.",
        )
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY가 설정되지 않았습니다.",
        )

    await ExamGenerationService.validate_documents(
        db,
        user.id,
        request.document_ids,
        require_indexed=request.generation_mode == "rag",
    )
    if request.exam_style_profile_id:
        await ExamGenerationService.load_style_profile(
            db, user.id, request.exam_style_profile_id
        )

    job = await JobService.create(db, user.id, request)
    background_tasks.add_task(generate_exam, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """생성 상태 조회"""
    return await JobService.get(db, user.id, job_id)


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """SSE 기반 생성 진행 상태 스트리밍"""

    async def event_generator():
        last_signature: tuple[str, int, str | None] | None = None
        while True:
            async with async_session() as db:
                try:
                    status_resp = await JobService.get(db, user.id, job_id)
                except HTTPException:
                    yield f"data: {json.dumps({'stage': 'FAILED', 'progress': 0, 'message': 'Job을 찾을 수 없습니다.'})}\n\n"
                    break

            signature = (status_resp.status, status_resp.progress, status_resp.message)
            if signature != last_signature:
                event = JobStreamEvent(
                    stage=status_resp.status,
                    progress=status_resp.progress,
                    message=status_resp.message,
                    exam_id=status_resp.exam_id,
                    token_usage=status_resp.token_usage,
                )
                yield f"data: {event.model_dump_json()}\n\n"
                last_signature = signature

            if status_resp.status in SSE_TERMINAL_STATUSES:
                break

            await asyncio.sleep(SSE_POLL_INTERVAL_SEC)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
