"""exam_generation_dedup 단위 테스트."""

import uuid

from app.schemas.exam import GeneratedQuestionPayload
from app.schemas.exam_generation import AnswerCandidate, GeneratedQuestionRecord
from app.services.exam_generation_dedup import (
    cosine_similarity,
    deduplicate_candidates,
    is_duplicate_question,
    normalize_text,
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
    def _candidate(self, concept: str, answer: str, chunk_id: uuid.UUID | None = None) -> AnswerCandidate:
        return AnswerCandidate(
            candidate_id=f"c_{concept[:4]}",
            concept=concept,
            answer_phrase=answer,
            evidence_chunk_id=chunk_id or uuid.uuid4(),
            evidence_text="근거 문장입니다.",
            question_type_hint="short_answer",
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
        concepts = {c.concept for c in result}
        assert "데드락" in concepts


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
            answer_phrase="정답1",
            evidence_chunk_id=uuid.uuid4(),
            evidence_text="근거",
            question_type_hint="short_answer",
        )
        previous = [
            GeneratedQuestionRecord(
                stem="질문 A",
                answer="정답2",
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
        candidate = candidate.model_copy(update={"question_type_hint": "short_answer"})
        result = validate_generated_question(payload, candidate, "LRU")
        assert result.is_valid is False


class TestCandidateSelection:
    def test_skips_used_candidates(self):
        cid = uuid.uuid4()
        candidates = [
            AnswerCandidate(
                candidate_id="used",
                concept="A",
                answer_phrase="a1",
                evidence_chunk_id=cid,
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
            candidates, used_candidate_ids={"used"}, chunk_usage_count={}
        )
        assert selected is not None
        assert selected.candidate_id == "free"
