"""페이지 기준 chunking.

각 페이지 텍스트를 글자 수 기준 슬라이딩 윈도(size/overlap)로 분할한다.
출처 추적을 위해 chunk는 페이지 경계를 넘지 않으며 page_start == page_end로 둔다.
"""

from dataclasses import dataclass

from app.services.extraction_service import PageText


@dataclass
class Chunk:
    chunk_index: int
    content: str
    page_start: int
    page_end: int
    source: str = "text"


def _sliding_window(text: str, size: int, overlap: int) -> list[str]:
    """글자 수 기준 슬라이딩 윈도로 텍스트를 분할한다."""
    if size <= 0:
        return [text] if text else []
    if len(text) <= size:
        return [text]

    step = max(size - overlap, 1)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + size].strip()
        if piece:
            pieces.append(piece)
        if start + size >= len(text):
            break
        start += step
    return pieces


class ChunkService:
    @staticmethod
    def chunk_pages(pages: list[PageText], chunk_size: int, overlap: int) -> list[Chunk]:
        """페이지별 텍스트를 chunk 리스트로 변환한다."""
        chunks: list[Chunk] = []
        index = 0
        for page in pages:
            text = page.text.strip()
            if not text:
                continue
            for piece in _sliding_window(text, chunk_size, overlap):
                chunks.append(
                    Chunk(
                        chunk_index=index,
                        content=piece,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        source=page.source,
                    )
                )
                index += 1
        return chunks
