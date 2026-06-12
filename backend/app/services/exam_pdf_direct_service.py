"""PDF_DIRECT 벤치마크: MinIO PDF 원본 → OpenAI API 직접 입력 → 배치 생성."""

import base64
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infra import minio_client
from app.models.concept import QuestionConcept
from app.models.exam import ExamGenerationJob, GeneratedExam, GeneratedQuestion
from app.models.exam_style import ExamStyleProfile
from app.schemas.exam import ExamGenerationRequest
from app.services.document_text_service import DocumentTextService
from app.services.exam_batch_generation import build_batch_user_prompt, generate_batch_from_messages
from app.services.exam_generation_service import ExamGenerationService

logger = logging.getLogger(__name__)


class ExamPdfDirectService:
    @classmethod
    async def run_job(cls, db: AsyncSession, job: ExamGenerationJob) -> uuid.UUID:
        from app.services.job_service import JobService

        job_id = job.id
        request = ExamGenerationRequest.model_validate(job.options or {})

        await JobService.update_progress_by_id(job_id, "GENERATING", 5, "문서 확인 중...")
        documents = await DocumentTextService.load_documents(
            db,
            job.user_id,
            request.document_ids,
            require_indexed=False,
        )
        style_profile: ExamStyleProfile | None = None
        if request.exam_style_profile_id:
            style_profile = await ExamGenerationService.load_style_profile(
                db, job.user_id, request.exam_style_profile_id
            )

        await JobService.update_progress_by_id(
            job_id, "GENERATING", 20, "PDF 다운로드 중..."
        )
        pdf_parts, total_bytes = await cls._build_pdf_message_parts(documents)
        logger.info(
            "Job %s PDF_DIRECT: %d개 PDF, %d bytes",
            job_id,
            len(pdf_parts),
            total_bytes,
        )

        doc_names = ", ".join(d.filename for d in documents)
        user_prompt = build_batch_user_prompt(
            request,
            material_section=f"[첨부 PDF]\n{doc_names}",
            style_profile=style_profile,
            source_label="첨부된 PDF 원본",
        )
        system_prompt = (
            "당신은 대학 강의자료 PDF만 보고 시험 문제를 만드는 출제 전문가입니다. "
            "첨부 PDF 범위를 벗어난 내용은 쓰지 마세요. JSON만 출력하세요."
        )

        await JobService.update_progress_by_id(
            job_id,
            "GENERATING",
            40,
            "LLM 배치 생성 중 (PDF 원본 입력)...",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    *pdf_parts,
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]
        payloads = await generate_batch_from_messages(request, messages)

        base_title = request.title or f"생성 문제집 {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
        title = (
            f"[PDF] {base_title}" if not base_title.startswith("[PDF]") else base_title
        )

        exam = GeneratedExam(
            job_id=job.id,
            user_id=job.user_id,
            title=title,
            question_count=len(payloads),
        )
        db.add(exam)
        await db.flush()

        for index, payload in enumerate(payloads, start=1):
            question = GeneratedQuestion(
                exam_id=exam.id,
                number=index,
                question_type=payload.question_type,
                difficulty=payload.difficulty,
                bloom_level=payload.bloom_level,
                stem=payload.stem,
                choices=payload.choices,
                answer=payload.answer,
                explanation=payload.explanation,
                source_chunk_ids=None,
            )
            db.add(question)
            await db.flush()
            for concept in (payload.concepts or [])[:5]:
                db.add(
                    QuestionConcept(question_id=question.id, concept=str(concept)[:200])
                )

        await JobService.update_progress_by_id(job_id, "FINALIZING", 92, "문제집 저장 중...")
        await db.commit()
        logger.info("Job %s PDF_DIRECT 완료: %d문항", job_id, len(payloads))
        return exam.id

    @classmethod
    async def _build_pdf_message_parts(
        cls,
        documents: list,
    ) -> tuple[list[dict], int]:
        parts: list[dict] = []
        total_bytes = 0
        max_bytes = settings.EXAM_MAX_UPLOAD_BYTES

        for document in documents:
            pdf_bytes = await minio_client.download_file(document.minio_key)
            total_bytes += len(pdf_bytes)
            if len(pdf_bytes) > max_bytes:
                raise ValueError(
                    f"PDF가 너무 큽니다 ({document.filename}): "
                    f"{len(pdf_bytes)} bytes (최대 {max_bytes})"
                )
            b64 = base64.b64encode(pdf_bytes).decode("ascii")
            parts.append(
                {
                    "type": "file",
                    "file": {
                        "filename": document.filename,
                        "file_data": f"data:application/pdf;base64,{b64}",
                    },
                }
            )
        return parts, total_bytes
