"""usage_meter 단위 테스트."""

from app.infra.usage_meter import TokenUsage, parse_token_usage, record_chat_usage, start_usage_tracking


class _FakeUsage:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeResponse:
    def __init__(self, usage):
        self.usage = usage


def test_token_usage_accumulates_chat_and_embedding():
    usage = start_usage_tracking()
    record_chat_usage(
        _FakeResponse(_FakeUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
    )
    record_chat_usage(
        _FakeResponse(_FakeUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280))
    )
    usage.add_embedding(_FakeUsage(total_tokens=40))

    assert usage.llm_calls == 2
    assert usage.prompt_tokens == 300
    assert usage.completion_tokens == 130
    assert usage.embedding_tokens == 40
    assert usage.total_tokens == 470
    assert "470" in usage.format_summary()


def test_token_usage_to_dict():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, llm_calls=1)
    assert usage.to_dict()["total_tokens"] == 15


def test_parse_token_usage():
    assert parse_token_usage(None) is None
    assert parse_token_usage({"total_tokens": 100, "llm_calls": 2}) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 100,
        "embedding_tokens": 0,
        "llm_calls": 2,
        "embedding_calls": 0,
    }
