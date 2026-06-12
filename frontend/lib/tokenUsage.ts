import type { TokenUsageSummary } from "@/lib/api";

export function formatTokenUsageShort(usage: TokenUsageSummary): string {
  return `${usage.total_tokens.toLocaleString()} tokens`;
}

export function formatTokenUsageDetail(usage: TokenUsageSummary): string {
  const parts = [
    `LLM ${usage.llm_calls ?? 0}회`,
    `입력 ${usage.prompt_tokens.toLocaleString()}`,
    `출력 ${usage.completion_tokens.toLocaleString()}`,
  ];
  if (usage.embedding_tokens) {
    parts.push(
      `임베딩 ${usage.embedding_tokens.toLocaleString()} (${usage.embedding_calls ?? 0}회)`
    );
  }
  parts.push(`합계 ${usage.total_tokens.toLocaleString()} tokens`);
  return parts.join(" · ");
}
