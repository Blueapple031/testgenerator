"""FULL_CONTEXT 벤치마크 스키마·유틸 단위 테스트."""


def test_truncate_for_context_pure():
    """DocumentTextService.truncate_for_context와 동일 로직 스모크."""

    def truncate(text: str, max_chars: int) -> tuple[str, bool]:
        if len(text) <= max_chars:
            return text, False
        truncated = text[:max_chars]
        cut_at = truncated.rfind("\n\n")
        if cut_at > max_chars * 0.7:
            truncated = truncated[:cut_at]
        return truncated + "\n\n[... 본문이 토큰 한도로 잘렸습니다 ...]", True

    result, was_truncated = truncate("a" * 1000, 500)
    assert was_truncated is True
    assert "잘렸습니다" in result


def test_generation_mode_schema_default():
    from app.schemas.exam import ExamGenerationRequest

    req = ExamGenerationRequest(
        document_ids=["00000000-0000-0000-0000-000000000001"],
    )
    assert req.generation_mode == "rag"


def test_generation_mode_full_context_alias():
    from app.schemas.exam import ExamGenerationRequest

    req = ExamGenerationRequest(
        document_ids=["00000000-0000-0000-0000-000000000001"],
        generation_mode="full",
    )
    assert req.generation_mode == "full_context"
