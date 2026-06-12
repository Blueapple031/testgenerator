"""FULL_CONTEXT / PDF_DIRECT 공통 배치 프롬프트 (순수 함수)."""

from app.schemas.exam import ExamGenerationRequest

TYPE_LABELS = {
    "multiple_choice": "객관식",
    "short_answer": "단답형",
    "essay_short": "짧은 서술형",
    "essay_long": "긴 서술형",
}


def type_mix_instruction(request: ExamGenerationRequest) -> str:
    lines = ["- 유형 배분 (순환):"]
    for i in range(request.question_count):
        t = request.question_types[i % len(request.question_types)]
        lines.append(f"  {i + 1}번: {TYPE_LABELS.get(t, t)} ({t})")
    return "\n".join(lines)


def build_style_section(style_profile) -> str:
    if not style_profile:
        return ""
    return f"""
[족보 출제 스타일]
- 유형 분포: {style_profile.type_distribution}
- Bloom: {style_profile.bloom_distribution}
- 주요 개념: {style_profile.common_concepts}
- 메모: {style_profile.style_notes or '없음'}"""


def build_page_range_note(request: ExamGenerationRequest) -> str:
    if request.page_range_start is None and request.page_range_end is None:
        return ""
    start = request.page_range_start or 1
    end = request.page_range_end or "끝"
    return f"- 출제 페이지 범위: p.{start} ~ p.{end} (이 범위를 우선 반영)"


def build_batch_user_prompt(
    request: ExamGenerationRequest,
    *,
    material_section: str,
    style_profile,
    source_label: str,
) -> str:
    types = ", ".join(TYPE_LABELS.get(t, t) for t in request.question_types)
    type_mix = type_mix_instruction(request)
    style_section = build_style_section(style_profile)
    page_note = build_page_range_note(request)

    return f"""{source_label}를 읽고 시험 문제 {request.question_count}개를 한 번에 생성하세요.

[생성 조건]
- 문항 수: 정확히 {request.question_count}개
- 허용 유형: {types}
{type_mix}
- 난이도: {request.difficulty}
{page_note}
- 정의·설명형 stem에는 개념명만 answer로 두지 말고 서술형 모범답 작성
- 객관식은 보기 4개(A~D), 정답 1개
- 문항 간 concept 중복 최소화
{style_section}

{material_section}

[출력 JSON]
{{
  "questions": [
    {{
      "stem": "문제 지문",
      "question_type": "essay_short",
      "difficulty": "{request.difficulty}",
      "bloom_level": "understand",
      "choices": null,
      "answer": "모범답",
      "explanation": "해설",
      "concepts": ["개념"]
    }}
  ]
}}"""
