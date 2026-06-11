"""그림/다이어그램 포함 페이지를 멀티모달 LLM으로 보강한다.

선택적 인덱싱: 그림이 있는 페이지만 vision으로 설명을 생성하므로 비용을 제어한다.
vision이 비활성화돼 있거나 API 키가 없거나 호출이 실패하면 원본 페이지를 유지해
인덱싱 파이프라인이 중단되지 않게 한다.
"""

import asyncio
import functools
import logging

from app.config import settings
from app.infra.vision_client import describe_page_image
from app.services.extraction_service import ExtractionService, PageText, render_page_png

logger = logging.getLogger(__name__)


async def enrich_pages_with_vision(pdf_bytes: bytes, pages: list[PageText]) -> list[PageText]:
    """그림이 포함된 페이지를 vision 설명으로 대체한 새 페이지 리스트를 반환한다."""
    if not settings.VISION_ENABLED or not settings.OPENAI_API_KEY:
        logger.info("Vision 보강 비활성화 또는 API 키 없음 — 원본 텍스트 유지")
        return pages

    target_pages = [p for p in pages if ExtractionService.page_needs_vision(p)]
    if not target_pages:
        return pages

    loop = asyncio.get_running_loop()
    vision_text_by_page: dict[int, str] = {}
    request_delay = settings.VISION_REQUEST_DELAY_MS / 1000.0

    for index, page in enumerate(target_pages):
        if index > 0 and request_delay > 0:
            await asyncio.sleep(request_delay)
        try:
            image = await loop.run_in_executor(
                None, functools.partial(render_page_png, pdf_bytes, page.page_number)
            )
            description = await describe_page_image(image)
            if description:
                vision_text_by_page[page.page_number] = _merge(page.text, description)
        except Exception:
            logger.exception("페이지 %d vision 보강 실패 — 원본 텍스트 유지", page.page_number)

    if not vision_text_by_page:
        return pages

    logger.info("Vision 보강 완료: %d개 페이지", len(vision_text_by_page))
    return [
        PageText(
            page_number=p.page_number,
            text=vision_text_by_page.get(p.page_number, p.text),
            has_images=p.has_images,
            drawing_count=p.drawing_count,
            source="vision" if p.page_number in vision_text_by_page else p.source,
        )
        for p in pages
    ]


def _merge(original_text: str, description: str) -> str:
    """vision 설명을 본문으로 사용하되, 원본 텍스트 레이어가 풍부하면 함께 보존한다."""
    original = original_text.strip()
    if ExtractionService._meaningful_char_count(original) >= 40 and original not in description:
        return f"{description}\n\n[원문 텍스트]\n{original}"
    return description
