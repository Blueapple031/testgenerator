"""exam_generation_dedup 단위 테스트."""

import uuid

from app.schemas.exam import GeneratedQuestionPayload
from app.schemas.exam_generation import AnswerCandidate, GeneratedQuestionRecord
from app.services.exam_generation_dedup import (
    cosine_similarity,
    deduplicate_candidates,
    is_duplicate_question,
    normalize_text,
    outline_coverage,
    select_candidate_for_question,
    validate_generated_question,
)


class TestNormalizeText:
    def test_round_robin_variants(self):
        a = normalize_text("Round Robin")
        b = normalize_text("round-robin")
        c = normalize_text(" ROUND   ROBIN ")
        assert a == b == c


class TestDeduplicateCandidates:
    def _candidate(
        self,
        concept: str,
        answer: str,
        chunk_id: uuid.UUID | None = None,
        *,
        qtype: str = "short_answer",
        angle: str = "definition",
        outline: list[str] | None = None,
    ) -> AnswerCandidate:
        return AnswerCandidate(
            candidate_id=f"c_{concept[:4]}_{angle}",
            concept=concept,
            answer_phrase=answer,
            answer_outline=outline or [],
            evidence_chunk_id=chunk_id or uuid.uuid4(),
            evidence_text="근거 문장입니다.",
            question_type_hint=qtype,
            question_angle=angle,
        )

    def test_same_concept_variants_removed(self):
        cid = uuid.uuid4()
        candidates = [
            self._candidate("프로세스 스케줄링", "CPU 스케줄링", cid),
            self._candidate("CPU 프로세스 스케줄링", "선점형 스케줄링", cid),
            self._candidate("데드락", "교착 상태", uuid.uuid4()),
        ]
        result = deduplicate_candidates(candidates)
        assert len(result) == 2

    def test_essay_same_concept_different_angle_kept(self):
        candidates = [
            self._candidate(
                "SPOF",
                "",
                qtype="essay_short",
                angle="definition",
                outline=["정의", "중요성"],
            ),
            self._candidate(
                "SPOF",
                "",
                qtype="essay_short",
                angle="comparison",
                outline=["HA 비교", "SPOF 완화"],
            ),
        ]
        result = deduplicate_candidates(candidates)
        assert len(result) == 2


class TestOutlineCoverage:
    def test_coverage_counts_outline_points(self):
        answer = (
            "단일 실패 지점은 한 구성요소 장애로 전체가 중단되는 구조이다. "
            "클라우드에서는 이중화로 완화한다."
        )
        outline = ["단일 실패 지점 정의", "클라우드 이중화 완화"]
        assert outline_coverage(answer, outline) >= 0.5


class TestEssayValidation:
    def _essay_candidate(self) -> AnswerCandidate:
        return AnswerCandidate(
            candidate_id="e1",
            concept="single_point_of_failure",
            answer_outline=[
                "SPOF 정의",
                "클라우드 HA/이중화",
                "가용성 영향",
            ],
            evidence_chunk_id=uuid.uuid4(),
            evidence_text="단일 실패 지점 SPOF 이중화",
            question_type_hint="essay_short",
            question_angle="definition",
        )

    def test_short_answer_as_concept_only_fails(self):
        payload = GeneratedQuestionPayload(
            stem="단일 실패 지점의 중요성을 설명하고 논하시오.",
            question_type="essay_short",
            difficulty="medium",
            answer="단일 실패 지점",
        )
        result = validate_generated_question(payload, self._essay_candidate(), "evidence")
        assert result.is_valid is False

    def test_valid_essay_passes(self):
        payload = GeneratedQuestionPayload(
            stem="SPOF를 정의하고 클라우드에서의 완화 방안을 서술하시오.",
            question_type="essay_short",
            difficulty="medium",
            answer=(
                "단일 실패 지점(SPOF)은 특정 구성요소 장애 시 전체 서비스가 중단될 수 있는 구조이다. "
                "클라우드에서는 다중 AZ, 로드밸런서, 이중화로 SPOF를 완화한다. "
                "SPOF가 남으면 SLA와 가용성 목표 달성이 어렵다."
            ),
        )
        result = validate_generated_question(payload, self._essay_candidate(), "SPOF 이중화")
        assert result.is_valid is True


class TestStemDuplicateDetection:
    def test_similar_stems_detected_via_fallback(self):
        payload = GeneratedQuestionPayload(
            stem="What are the four necessary conditions for deadlock?",
            question_type="short_answer",
            difficulty="medium",
            answer="mutual exclusion, hold and wait, no preemption, circular wait",
            concepts=["deadlock"],
        )
        candidate = AnswerCandidate(
            candidate_id="c1",
            concept="deadlock",
            answer_phrase="mutual exclusion, hold and wait, no preemption, circular wait",
            evidence_chunk_id=uuid.uuid4(),
            evidence_text="four conditions for deadlock",
            question_type_hint="short_answer",
        )
        previous = [
            GeneratedQuestionRecord(
                stem="What are the four necessary conditions for deadlock to occur?",
                answer="other answer",
                concepts=["deadlock_conditions"],
            )
        ]
        is_dup, reason = is_duplicate_question(payload, candidate, previous)
        assert is_dup is True
        assert "stem" in reason

    def test_embedding_similarity_duplicate(self):
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.99, 0.01, 0.0]
        payload = GeneratedQuestionPayload(
            stem="Question B about scheduling",
            question_type="short_answer",
            difficulty="medium",
            answer="answer1",
            concepts=["topic_a"],
        )
        candidate = AnswerCandidate(
            candidate_id="c1",
            concept="topic_a",
            answer_phrase="answer1",
            evidence_chunk_id=uuid.uuid4(),
            evidence_text="근거",
            question_type_hint="short_answer",
        )
        previous = [
            GeneratedQuestionRecord(
                stem="Question A",
                answer="answer2",
                concepts=["topic_b"],
                stem_embedding=vec_a,
            )
        ]
        is_dup, _ = is_duplicate_question(
            payload, candidate, previous, stem_embedding=vec_b
        )
        assert is_dup is True
        assert cosine_similarity(vec_a, vec_b) >= 0.85


class TestMultipleChoiceValidation:
    def _base_candidate(self) -> AnswerCandidate:
        return AnswerCandidate(
            candidate_id="c1",
            concept="LRU",
            answer_phrase="LRU",
            evidence_chunk_id=uuid.uuid4(),
            evidence_text="LRU는 least recently used 페이지 교체",
            question_type_hint="multiple_choice",
        )

    def test_answer_not_in_choices_fails(self):
        payload = GeneratedQuestionPayload(
            stem="페이지 교체 알고리즘은?",
            question_type="multiple_choice",
            difficulty="medium",
            answer="LRU",
            choices=[
                {"label": "A", "text": "FIFO", "isAnswer": False},
                {"label": "B", "text": "OPT", "isAnswer": False},
            ],
        )
        result = validate_generated_question(payload, self._base_candidate(), "LRU 알고리즘")
        assert result.is_valid is False
        assert "choices" in result.reason

    def test_duplicate_choices_fail(self):
        payload = GeneratedQuestionPayload(
            stem="페이지 교체 알고리즘은?",
            question_type="multiple_choice",
            difficulty="medium",
            answer="LRU",
            choices=[
                {"label": "A", "text": "LRU", "isAnswer": True},
                {"label": "B", "text": "LRU", "isAnswer": False},
            ],
        )
        result = validate_generated_question(payload, self._base_candidate(), "LRU 알고리즘")
        assert result.is_valid is False

    def test_empty_stem_fails(self):
        payload = GeneratedQuestionPayload.model_construct(
            stem="",
            question_type="short_answer",
            difficulty="medium",
            answer="LRU",
            concepts=[],
            choices=None,
            explanation=None,
            bloom_level=None,
        )
        candidate = self._base_candidate()
        result = validate_generated_question(payload, candidate, "LRU")
        assert result.is_valid is False


class TestCandidateSelection:
    def test_prefers_matching_question_type(self):
        candidates = [
            AnswerCandidate(
                candidate_id="short",
                concept="A",
                answer_phrase="a1",
                evidence_chunk_id=uuid.uuid4(),
                evidence_text="text",
                question_type_hint="short_answer",
            ),
            AnswerCandidate(
                candidate_id="essay",
                concept="B",
                answer_outline=["요지1", "요지2"],
                evidence_chunk_id=uuid.uuid4(),
                evidence_text="text",
                question_type_hint="essay_short",
                question_angle="definition",
            ),
        ]
        selected = select_candidate_for_question(
            candidates,
            used_candidate_ids=set(),
            chunk_usage_count={},
            question_type="essay_short",
        )
        assert selected is not None
        assert selected.candidate_id == "essay"

    def test_skips_used_candidates(self):
        candidates = [
            AnswerCandidate(
                candidate_id="used",
                concept="A",
                answer_phrase="a1",
                evidence_chunk_id=uuid.uuid4(),
                evidence_text="text",
                question_type_hint="short_answer",
            ),
            AnswerCandidate(
                candidate_id="free",
                concept="B",
                answer_phrase="b1",
                evidence_chunk_id=uuid.uuid4(),
                evidence_text="text",
                question_type_hint="short_answer",
            ),
        ]
        selected = select_candidate_for_question(
            candidates,
            used_candidate_ids={"used"},
            chunk_usage_count={},
            question_type="short_answer",
        )
        assert selected is not None
        assert selected.candidate_id == "free"
