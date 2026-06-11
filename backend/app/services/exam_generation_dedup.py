"""시험 생성 중복 제거·검증 순수 로직 (단위 테스트 대상)."""

import re
import uuid
from difflib import SequenceMatcher

from app.config import settings
from app.schemas.exam import GeneratedQuestionPayload
from app.schemas.exam_generation import (
    ESSAY_TYPES,
    ESSAY_REQUIRED_ANGLES,
    AnswerCandidate,
    GeneratedQuestionRecord,
    QuestionValidationResult,
)

EXPLANATORY_STEM_MARKERS = (
    "설명",
    "논하",
    "서술",
    "정의",
    "기술",
    "비교",
    "분석",
    "discuss",
    "explain",
    "describe",
    "define",
)


def normalize_text(text: str) -> str:
    """비교용 문자열 정규화: 소문자, alphanumeric+한글만 유지."""
    lowered = text.lower().strip()
    return re.sub(r"[\s\W_]+", "", lowered, flags=re.UNICODE)


def is_essay_type(question_type: str) -> bool:
    return question_type in ESSAY_TYPES


def stem_requires_explanation(stem: str) -> bool:
    """stem이 정의·설명·서술 등 장문 답을 요구하는지."""
    return any(marker in stem for marker in EXPLANATORY_STEM_MARKERS)


def answer_is_concept_label(
    answer: str,
    candidate: AnswerCandidate,
    *,
    question_type: str = "",
) -> bool:
    """정답이 개념명·answer_phrase 한 줄뿐인지 (단답 키워드 정답은 제외)."""
    norm_answer = normalize_text(answer)
    if not norm_answer:
        return True
    norm_concept = normalize_text(candidate.concept)
    norm_phrase = normalize_text(candidate.answer_phrase or "")

    if question_type in {"short_answer", "multiple_choice"}:
        # phrase가 concept와 다르고 정답이 phrase와 일치 → 정상 단답 (예: concept=LRU 알고리즘, phrase=LRU)
        if norm_phrase and norm_answer == norm_phrase and norm_phrase != norm_concept:
            return False

    if norm_concept and norm_answer == norm_concept:
        return True
    if norm_phrase and norm_concept and norm_phrase == norm_concept and norm_answer == norm_concept:
        return True
    return False


def _validate_stem_answer_alignment(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
) -> QuestionValidationResult | None:
    """유형·각도·stem·정답 길이 교차 검증. None이면 통과."""
    needs_essay = (
        stem_requires_explanation(payload.stem)
        or candidate.question_angle in ESSAY_REQUIRED_ANGLES
    )
    if needs_essay and not is_essay_type(payload.question_type):
        return QuestionValidationResult(
            is_valid=False,
            reason="stem/출제각도가 서술을 요구하지만 단답·객관식 유형",
        )
    if answer_is_concept_label(payload.answer, candidate, question_type=payload.question_type):
        if is_essay_type(payload.question_type) or needs_essay or stem_requires_explanation(
            payload.stem
        ):
            return QuestionValidationResult(
                is_valid=False,
                reason="정답이 개념명 한 줄뿐이며 설명·서술 요구와 불일치",
            )
    return None


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


def _candidate_dedup_key(candidate: AnswerCandidate) -> str:
    if candidate.question_type_hint in ESSAY_TYPES:
        return f"{normalize_text(candidate.concept)}:{candidate.question_angle}"
    phrase = normalize_text(candidate.answer_phrase or candidate.concept)
    return f"{normalize_text(candidate.concept)}:{phrase}"


def outline_coverage(answer: str, outline: list[str]) -> float:
    """answer가 outline 요지를 얼마나 포함하는지 (0~1)."""
    if not outline:
        return 1.0
    answer_norm = normalize_text(answer)
    hits = 0
    for point in outline:
        point_norm = normalize_text(point)
        if not point_norm:
            continue
        window = min(12, len(point_norm))
        if point_norm in answer_norm or point_norm[:window] in answer_norm:
            hits += 1
            continue
        for token in point.split():
            if len(token) >= 2 and normalize_text(token) in answer_norm:
                hits += 1
                break
    return hits / len(outline)


def deduplicate_candidates(candidates: list[AnswerCandidate]) -> list[AnswerCandidate]:
    """유형별 키(concept+angle 또는 concept+phrase)로 후보 중복 제거."""
    seen_keys: set[str] = set()
    seen_concepts: set[str] = set()
    result: list[AnswerCandidate] = []

    for candidate in candidates:
        key = _candidate_dedup_key(candidate)
        if key in seen_keys:
            continue
        if any(_concepts_overlap(candidate.concept, prev) for prev in seen_concepts):
            if candidate.question_type_hint not in ESSAY_TYPES:
                continue

        seen_keys.add(key)
        seen_concepts.add(normalize_text(candidate.concept))
        result.append(candidate)

    return result


def select_candidate_for_question(
    candidates: list[AnswerCandidate],
    used_candidate_ids: set[str],
    chunk_usage_count: dict[str, int],
    question_type: str,
    used_angles: set[str] | None = None,
) -> AnswerCandidate | None:
    """요청 유형과 일치하는 미사용 후보만 선택 (유형 불일치 후보 제외)."""
    used_angles = used_angles or set()
    available = [
        c
        for c in candidates
        if c.candidate_id not in used_candidate_ids
        and c.question_type_hint == question_type
        and not (
            question_type in {"short_answer", "multiple_choice"}
            and c.question_angle in ESSAY_REQUIRED_ANGLES
        )
    ]

    if not available:
        return None

    def sort_key(c: AnswerCandidate) -> tuple[int, int, str]:
        angle_used = 1 if c.question_angle in used_angles else 0
        chunk_usage = chunk_usage_count.get(str(c.evidence_chunk_id), 0)
        return (angle_used, chunk_usage, c.candidate_id)

    return min(available, key=sort_key)


def _validate_short_answer(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
    evidence_content: str,
) -> QuestionValidationResult:
    norm_expected = normalize_text(candidate.answer_phrase or candidate.concept)
    norm_actual = normalize_text(payload.answer)
    if not norm_actual:
        return QuestionValidationResult(is_valid=False, reason="정답이 비어 있음")

    if stem_requires_explanation(payload.stem):
        return QuestionValidationResult(
            is_valid=False,
            reason="stem은 설명·정의를 요구하지만 단답형",
        )

    if answer_is_concept_label(payload.answer, candidate, question_type=payload.question_type):
        return QuestionValidationResult(
            is_valid=False,
            reason="단답 정답이 개념명만 반복됨",
        )

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
    phrase_lower = (candidate.answer_phrase or "").lower().strip()
    if phrase_lower and phrase_lower not in evidence_lower:
        snippet = candidate.evidence_text.lower().strip()
        if snippet and snippet[: min(20, len(snippet))] not in evidence_lower:
            return QuestionValidationResult(
                is_valid=False,
                reason="근거 chunk에서 정답 또는 근거 문장을 확인할 수 없음",
            )
    return QuestionValidationResult(is_valid=True, reason="단답 검증 통과")


def _validate_essay(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
) -> QuestionValidationResult:
    min_len = (
        settings.EXAM_GEN_ESSAY_LONG_MIN_ANSWER_LEN
        if payload.question_type == "essay_long"
        else settings.EXAM_GEN_ESSAY_SHORT_MIN_ANSWER_LEN
    )
    answer = payload.answer.strip()
    if len(answer) < min_len:
        return QuestionValidationResult(
            is_valid=False,
            reason=f"서술형 정답이 너무 짧음 (최소 {min_len}자)",
        )

    norm_answer = normalize_text(answer)
    norm_concept = normalize_text(candidate.concept)
    if norm_answer == norm_concept or len(norm_answer) < 15:
        return QuestionValidationResult(
            is_valid=False,
            reason="정답이 개념명 한 줄뿐이며 서술형 요구와 불일치",
        )

    if candidate.answer_outline:
        coverage = outline_coverage(answer, candidate.answer_outline)
        if coverage < settings.EXAM_GEN_OUTLINE_COVERAGE_RATIO:
            return QuestionValidationResult(
                is_valid=False,
                reason=f"answer_outline 요지 반영 부족 ({coverage:.0%})",
            )

    essay_markers = ("설명", "논하", "서술", "비교", "분석", "论述")
    if any(m in payload.stem for m in essay_markers) and len(answer) < min_len:
        return QuestionValidationResult(is_valid=False, reason="stem은 서술형인데 정답이 짧음")

    return QuestionValidationResult(is_valid=True, reason="서술형 검증 통과")


def validate_generated_question(
    payload: GeneratedQuestionPayload,
    candidate: AnswerCandidate,
    evidence_content: str,
) -> QuestionValidationResult:
    """유형별 규칙 기반 문제·정답 정합성 검증."""
    if not payload.stem or len(payload.stem.strip()) < 5:
        return QuestionValidationResult(is_valid=False, reason="stem이 비어 있거나 너무 짧음")

    alignment = _validate_stem_answer_alignment(payload, candidate)
    if alignment is not None:
        return alignment

    if is_essay_type(payload.question_type):
        result = _validate_essay(payload, candidate)
        if not result.is_valid:
            return result
    else:
        result = _validate_short_answer(payload, candidate, evidence_content)
        if not result.is_valid:
            return result

    if payload.question_type == "multiple_choice":
        if not payload.choices or len(payload.choices) < 2:
            return QuestionValidationResult(is_valid=False, reason="객관식 보기가 부족함")

        choice_texts = [normalize_text(c.get("text", "")) for c in payload.choices]
        if len(choice_texts) != len(set(choice_texts)):
            return QuestionValidationResult(is_valid=False, reason="choices에 중복 선택지 존재")

        norm_actual = normalize_text(payload.answer)
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
        if (
            candidate.question_angle
            and record.question_angle == candidate.question_angle
            and any(_concepts_overlap(candidate.concept, c) for c in record.concepts)
        ):
            return True, "동일 concept+angle 중복"

        norm_existing_answer = normalize_text(record.answer)
        if norm_new_answer == norm_existing_answer and not is_essay_type(payload.question_type):
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
