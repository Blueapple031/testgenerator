"""EMBEDDING_PROVIDER 환경변수에 따라 로컬 모델 또는 OpenAI 임베딩 분기.

MVP는 OpenAI(text-embedding-3-small, 1536차원)를 사용하고,
로컬 모델(sentence-transformers) 전환은 Phase 8에서 구현한다.
"""

from app.config import settings


async def get_embedding(text: str) -> list[float]:
    embeddings = await get_embeddings([text])
    return embeddings[0]


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.EMBEDDING_PROVIDER == "local":
        return await _local_embeddings(texts)
    return await _openai_embeddings(texts)


async def _local_embeddings(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError("로컬 임베딩 모델 로딩은 Phase 8에서 구현")


async def _openai_embeddings(texts: list[str]) -> list[list[float]]:
    from app.infra.llm_client import openai_client

    response = await openai_client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    # OpenAI는 입력 순서를 보장하지만 index로 한 번 더 정렬해 안전하게 반환한다.
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]
