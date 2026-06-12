"""시험 생성 Job 단위 OpenAI 토큰 사용량 집계."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

_current_usage: ContextVar[TokenUsage | None] = ContextVar("exam_job_token_usage", default=None)


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    embedding_tokens: int = 0
    llm_calls: int = 0
    embedding_calls: int = 0

    def add_chat(self, usage: Any) -> None:
        if not usage:
            return
        self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)
        self.llm_calls += 1

    def add_embedding(self, usage: Any) -> None:
        if not usage:
            return
        tokens = int(getattr(usage, "total_tokens", 0) or 0)
        self.embedding_tokens += tokens
        self.total_tokens += tokens
        self.embedding_calls += 1

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "embedding_tokens": self.embedding_tokens,
            "llm_calls": self.llm_calls,
            "embedding_calls": self.embedding_calls,
        }

    def format_summary(self) -> str:
        parts = [
            f"LLM {self.llm_calls}회",
            f"입력 {self.prompt_tokens:,}",
            f"출력 {self.completion_tokens:,}",
        ]
        if self.embedding_tokens:
            parts.append(f"임베딩 {self.embedding_tokens:,} ({self.embedding_calls}회)")
        parts.append(f"합계 {self.total_tokens:,} tokens")
        return " · ".join(parts)


def start_usage_tracking() -> TokenUsage:
    usage = TokenUsage()
    _current_usage.set(usage)
    return usage


def get_usage() -> TokenUsage:
    return _current_usage.get() or TokenUsage()


def record_chat_usage(response: Any) -> None:
    usage = _current_usage.get()
    if usage is None:
        return
    usage.add_chat(getattr(response, "usage", None))


def record_embedding_usage(response: Any) -> None:
    usage = _current_usage.get()
    if usage is None:
        return
    usage.add_embedding(getattr(response, "usage", None))


def parse_token_usage(raw: Any) -> dict[str, int] | None:
    """Job options 등에서 token_usage dict 추출."""
    if not isinstance(raw, dict):
        return None
    keys = (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "embedding_tokens",
        "llm_calls",
        "embedding_calls",
    )
    parsed = {k: int(raw.get(k, 0) or 0) for k in keys}
    if parsed["total_tokens"] <= 0 and parsed["llm_calls"] <= 0:
        return None
    return parsed
