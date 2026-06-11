"""시험 생성 중복 제거·검증 순수 로직 (단위 테스트 대상)."""

import re
import uuid
from difflib import SequenceMatcher

from app.config import settings
from app.schemas.exam import GeneratedQuestionPayload
from app.schemas.exam_generation import (
    AnswerCandidate,
    GeneratedQuestionRecord,
    QuestionValidationResult,
)


def normalize_text(text: str) -> str:
    """비교용 문자열 정규화: 소문자, 알phanumeric+한글만 유지."""
    lowered = text.lower().strip()
    return re.sub(r"[\s\W_]+", "", lowered, flags=re.UNICODE)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _concepts_overlap(a: str, b: str) -> bool:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= settings.EXAM_GEN_CONCEPT_SIMILARITY_THRESHOLD


def deduplicate_candidates(candidates: list[AnswerCandidate]) -> list[AnswerCandidate]:
    """정답 phrase·concept·chunk 기준으로 후보 중복 제거."""
    seen_answers: set[str] = set()
    seen_concepts: set[str] = set()
    seen_chunk_concepts: set[tuple[str, str]] = set()
    result: list[AnswerCandidate] = []

    for candidate in candidates:
        norm_answer = normalize_text(candidate.answer_phrase)
        norm_concept = normalize_text(candidate.concept)
        chunk_key = (str(candidate.evidence_chunk_id), norm_concept)

        if norm_answer in seen_answers:
            continue
        if any(_concepts_overlap(candidate.concept, prev) for prev in seen_concepts):
            continue
        if chunk_key in seen_chunk_concepts:
            continue

        seen_answers.add(norm_answer)
        seen_concepts.add(norm_concept)
        seen_chunk_concepts.add(chunk_key)
        result.append(candidate)

    return result


def select_candidate_for_question(
    candidates: list[AnswerCandidate],
    used_candidate_ids: set[str],
    chunk_usage_count: dict[str, int],
) -> AnswerCandidate | None:
    """미사용 후보 중 evidence chunk 사용 횟수가 적은 후보를 우선 선택."""
    available = [c for c in candidates if c.candidate_id not in used_candidate_ids]
    if not available:
        return None

    def sort_key(c: AnswerCandidate) -> tuple[int, str]:
        usage = chunk_usage_count.get(str(c.evidence_chunk_id), 0)
        return (usage, c.candidate_id)

    return min(available, key=sort_key)


def validate_generated_question(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
    evidence_content: str,
) -> QuestionValidationResult:
    """규칙 기반 문제·정답 정합성 검증."""
    if not payload.stem or len(payload.stem.strip()) < 5:
        return QuestionValidationResult(is_valid=False, reason="stem이 비어 있거나 너무 짧음")

    norm_expected = normalize_text(candidate.answer_phrase)
    norm_actual = normalize_text(payload.answer)
    if not norm_actual:
        return QuestionValidationResult(is_valid=False, reason="정답이 비어 있음")

    answer_match = (
        norm_expected == norm_actual
        or norm_expected in norm_actual
        or norm_actual in norm_expected
    )
    if not answer_match:
        return QuestionValidationResult(
            is_valid=False,
            reason="정답이 answer_phrase와 일치하지 않음",
        )

    evidence_lower = evidence_content.lower()
    phrase_lower = candidate.answer_phrase.lower().strip()
    if phrase_lower and phrase_lower not in evidence_lower:
        snippet = candidate.evidence_text.lower().strip()
        if snippet and snippet[: min(20, len(snippet))] not in evidence_lower:
            return QuestionValidationResult(
                is_valid=False,
                reason="근거 chunk에서 정답 또는 근거 문장을 확인할 수 없음",
            )

    if payload.question_type == "multiple_choice":
        if not payload.choices or len(payload.choices) < 2:
            return QuestionValidationResult(is_valid=False, reason="객관식 보기가 부족함")

        choice_texts = [normalize_text(c.get("text", "")) for c in payload.choices]
        if len(choice_texts) != len(set(choice_texts)):
            return QuestionValidationResult(is_valid=False, reason="choices에 중복 선택지 존재")

        answer_in_choices = any(
            normalize_text(c.get("text", "")) == norm_actual
            or norm_actual in normalize_text(c.get("text", ""))
            for c in payload.choices
        )
        if not answer_in_choices:
            return QuestionValidationResult(is_valid=False, reason="정답이 choices에 포함되지 않음")

    return QuestionValidationResult(is_valid=True, reason="규칙 기반 검증 통과")


def is_duplicate_question(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
    previous: list[GeneratedQuestionRecord],
    *,
    stem_embedding: list[float] | None = None,
    concept_embedding: list[float] | None = None,
) -> tuple[bool, str]:
    """기존 승인 문항과 중복 여부 판정."""
    norm_new_answer = normalize_text(payload.answer)

    for record in previous:
        norm_existing_answer = normalize_text(record.answer)
        if norm_new_answer == norm_existing_answer:
            for existing_concept in record.concepts or [candidate.concept]:
                if _concepts_overlap(candidate.concept, existing_concept):
                    return True, "동일 정답+유사 concept"

        for existing_concept in record.concepts:
            if normalize_text(existing_concept) == normalize_text(candidate.concept):
                return True, "concept 중복"

        if concept_embedding and record.concept_embeddings:
            for existing_emb in record.concept_embeddings:
                if (
                    cosine_similarity(concept_embedding, existing_emb)
                    >= settings.EXAM_GEN_CONCEPT_SIMILARITY_THRESHOLD
                ):
                    return True, "concept embedding 유사도 초과"

        if stem_embedding and record.stem_embedding:
            sim = cosine_similarity(stem_embedding, record.stem_embedding)
            if sim >= settings.EXAM_GEN_STEM_SIMILARITY_THRESHOLD:
                return True, f"stem embedding 유사도 {sim:.2f}"

        if _stems_are_similar(payload.stem, record.stem):
            return True, "stem 문자열 유사"

    return False, ""


def _stems_are_similar(stem_a: str, stem_b: str) -> bool:
    """difflib ratio + 긴 공통 부분 문자열(한국어 유사 stem 대응)."""
    na, nb = normalize_text(stem_a), normalize_text(stem_b)
    if SequenceMatcher(None, na, nb).ratio() >= settings.EXAM_GEN_STEM_FALLBACK_RATIO:
        return True
    min_window = 12
    if len(na) >= min_window and len(nb) >= min_window:
        shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
        step = max(1, min_window // 3)
        for i in range(0, len(shorter) - min_window + 1, step):
            if shorter[i : i + min_window] in longer:
                return True
    return False


def resolve_chunk_id(raw_id: str, valid_ids: set[uuid.UUID]) -> uuid.UUID | None:
    """LLM이 반환한 chunk id를 실제 UUID로 매핑."""
    try:
        parsed = uuid.UUID(raw_id)
        if parsed in valid_ids:
            return parsed
    except ValueError:
        pass
    for vid in valid_ids:
        if str(vid).startswith(raw_id) or raw_id in str(vid):
            return vid
    return None
