"""chunk 임베딩 생성. 대량 입력은 배치로 나눠 임베딩 API를 호출한다."""

from app.infra.embedding_client import get_embeddings

# 한 번의 임베딩 요청에 보낼 최대 텍스트 수.
BATCH_SIZE = 96


class EmbeddingService:
    @staticmethod
    async def embed_texts(texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 배치로 나눠 임베딩 벡터 리스트를 반환한다."""
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            embeddings.extend(await get_embeddings(batch))
        return embeddings
