"""EMBEDDING_PROVIDER 환경변수에 따라 로컬 모델 또는 OpenAI 임베딩 분기"""

from app.config import settings


async def get_embedding(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "local":
        return await _local_embedding(text)
    return await _openai_embedding(text)


async def _local_embedding(text: str) -> list[float]:
    raise NotImplementedError("로컬 임베딩 모델 로딩은 Phase 8에서 구현")


async def _openai_embedding(text: str) -> list[float]:
    from app.infra.llm_client import openai_client

    response = await openai_client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding
