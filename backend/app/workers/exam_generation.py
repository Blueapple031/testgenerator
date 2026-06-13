"""비동기 시험 생성: RAG 검색 → LLM 호출 → JSON 검증 → DB 저장."""

import logging
import uuid

from app.database import async_session
from app.infra.usage_meter import get_usage, start_usage_tracking
from app.models.exam import ExamGenerationJob
from app.services.exam_generation_service import ExamGenerationService
from app.services.job_service import JobService
from app.services.pilot_account_service import PilotAccountService

logger = logging.getLogger(__name__)


async def generate_exam(job_id: uuid.UUID) -> None:
    """백그라운드에서 시험 생성 Job을 실행한다."""
    async with async_session() as db:
        job = await db.get(ExamGenerationJob, job_id)
        if job is None:
            logger.warning("시험 생성 Job 없음: %s", job_id)
            return

        try:
            start_usage_tracking()
            await JobService.update_progress_by_id(job_id, "GENERATING", 2, "시작...")
            exam_id = await ExamGenerationService.run_job(db, job)
            usage = get_usage()
            usage_data = usage.to_dict()
            completion_message = f"완료 · {usage.format_summary()}"
            await PilotAccountService.record_token_usage(db, job.user_id, usage_data.get("total_tokens", 0))
            await JobService.update_progress_by_id(
                job_id,
                "COMPLETED",
                100,
                completion_message,
                completed=True,
                token_usage=usage_data,
            )
            logger.info(
                "시험 생성 완료: job=%s exam=%s tokens=%s",
                job_id,
                exam_id,
                usage_data,
            )
        except Exception as exc:
            logger.exception("시험 생성 실패: job=%s", job_id)
            await db.rollback()
            await JobService.update_progress_by_id(
                job_id,
                "FAILED",
                0,
                f"시험 생성 실패: {exc}",
            )
