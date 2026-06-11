"""생성된 시험 조회 및 (개발용) 데모 시험 생성."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import QuestionConcept
from app.models.exam import ExamGenerationJob, GeneratedExam, GeneratedQuestion
from app.schemas.exam import ExamListItem, ExamResponse, QuestionResponse


class ExamService:
    @staticmethod
    async def list_exams(db: AsyncSession, user_id: uuid.UUID) -> list[ExamListItem]:
        stmt = (
            select(GeneratedExam)
            .where(GeneratedExam.user_id == user_id)
            .order_by(GeneratedExam.created_at.desc())
        )
        result = await db.execute(stmt)
        exams = result.scalars().all()
        return [
            ExamListItem(
                id=exam.id,
                title=exam.title,
                question_count=exam.question_count,
                created_at=exam.created_at,
            )
            for exam in exams
        ]

    @staticmethod
    async def get_exam(
        db: AsyncSession,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> ExamResponse:
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

        questions_result = await db.execute(
            select(GeneratedQuestion)
            .where(GeneratedQuestion.exam_id == exam_id)
            .order_by(GeneratedQuestion.number)
        )
        questions = list(questions_result.scalars().all())
        question_ids = [q.id for q in questions]
        concepts_by_question: dict[uuid.UUID, list[str]] = {qid: [] for qid in question_ids}
        if question_ids:
            concept_result = await db.execute(
                select(QuestionConcept).where(QuestionConcept.question_id.in_(question_ids))
            )
            for row in concept_result.scalars().all():
                concepts_by_question[row.question_id].append(row.concept)

        return ExamResponse(
            id=exam.id,
            title=exam.title,
            question_count=exam.question_count,
            created_at=exam.created_at,
            questions=[
                QuestionResponse(
                    id=q.id,
                    number=q.number,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    bloom_level=q.bloom_level,
                    stem=q.stem,
                    choices=q.choices,
                    answer=q.answer,
                    explanation=q.explanation,
                    concepts=concepts_by_question.get(q.id, []),
                )
                for q in questions
            ],
        )

    @classmethod
    async def create_demo_exam(cls, db: AsyncSession, user_id: uuid.UUID) -> ExamResponse:
        """Phase 5 UI 확인용 샘플 시험. Phase 4 완료 전까지 미리보기·인쇄 테스트에 사용."""
        job = ExamGenerationJob(
            user_id=user_id,
            status="COMPLETED",
            progress=100,
            message="데모 시험",
        )
        db.add(job)
        await db.flush()

        exam = GeneratedExam(
            job_id=job.id,
            user_id=user_id,
            title="클라우드 아키텍처 심화 — 데모 문제집",
            question_count=3,
        )
        db.add(exam)
        await db.flush()

        demo_questions = [
            {
                "number": 1,
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "bloom_level": "understand",
                "stem": "하이퍼바이저 클러스터링 아키텍처에서 물리 서버 장애 발생 시 가상 머신을 다른 호스트로 이관하는 주된 목적은 무엇인가?",
                "choices": [
                    {"label": "A", "text": "스토리지 용량 확장", "isAnswer": False},
                    {"label": "B", "text": "가용성 확보 및 서비스 연속성 유지", "isAnswer": True},
                    {"label": "C", "text": "네트워크 대역폭 증가", "isAnswer": False},
                    {"label": "D", "text": "라이선스 비용 절감", "isAnswer": False},
                ],
                "answer": "B",
                "explanation": "클러스터링은 장애 시 VM을 다른 하이퍼바이저로 이관해 서비스 중단을 최소화하는 것이 핵심이다.",
                "concepts": ["hypervisor_clustering", "high_availability"],
            },
            {
                "number": 2,
                "question_type": "short_answer",
                "difficulty": "medium",
                "bloom_level": "apply",
                "stem": "부하 분산 가상 머신 인스턴스 아키텍처에서 특정 물리 서버에 VM이 과도하게 집중되는 문제를 완화하는 방법을 한 가지 서술하시오.",
                "choices": None,
                "answer": "용량 관제(또는 스케줄링) 정책을 적용해 VM을 물리 서버에 고르게 분배한다.",
                "explanation": "작업 부하 분산만으로는 VM 배치 불균형이 남을 수 있어, 용량 관제 기반 재배치가 필요하다.",
                "concepts": ["load_balancing", "capacity_governance"],
            },
            {
                "number": 3,
                "question_type": "essay_short",
                "difficulty": "hard",
                "bloom_level": "analyze",
                "stem": "무중단 서비스 재배치 아키텍처와 라이브 VM 마이그레이션의 차이를 목적과 동작 방식 측면에서 비교하시오.",
                "choices": None,
                "answer": "무중단 재배치는 서비스 중단 없이 VM/서비스를 다른 호스트로 옮기는 운영 패턴이며, 라이브 VM 마이그레이션은 실행 중인 VM의 메모리·상태를 이전하는 구체적 기술이다. 전자는 아키텍처 목표, 후자는 구현 수단에 가깝다.",
                "explanation": "강의자료에서 무중단 재배치는 아키텍처 관점, live migration은 기술 메커니즘으로 구분해 설명한다.",
                "concepts": ["live_migration", "zero_downtime"],
            },
        ]

        for item in demo_questions:
            concepts = item.pop("concepts")
            question = GeneratedQuestion(exam_id=exam.id, **item)
            db.add(question)
            await db.flush()
            for concept in concepts:
                db.add(QuestionConcept(question_id=question.id, concept=concept))

        await db.commit()
        return await cls.get_exam(db, user_id, exam.id)
