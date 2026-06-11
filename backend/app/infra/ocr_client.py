"""Upstage OCR 기반 텍스트 추출 fallback.

PyMuPDF 텍스트 레이어가 부족한(스캔 이미지) 페이지만 이미지로 렌더링해
Upstage Document Digitization(OCR) API로 텍스트를 보강한다.

OCR가 비활성화돼 있거나 API 키가 없거나 호출이 실패하면
원본 페이지를 그대로 반환해 인덱싱 파이프라인이 중단되지 않게 한다.
"""

import asyncio
import functools
import logging

import httpx

from app.config import settings
from app.services.extraction_service import ExtractionService, PageText, render_page_png

logger = logging.getLogger(__name__)

UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"
HTTP_TIMEOUT = 60.0
# 백오프 상한(초). Retry-After 헤더가 없을 때 지수 백오프의 최대 대기 시간.
MAX_BACKOFF_SECONDS = 30.0


def _parse_ocr_text(payload: dict) -> str:
    """Upstage OCR 응답에서 텍스트를 추출한다. 스키마 변화에 방어적으로 대응."""
    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    pages = payload.get("pages")
    if isinstance(pages, list):
        collected = [
            page["text"]
            for page in pages
            if isinstance(page, dict) and isinstance(page.get("text"), str)
        ]
        if collected:
            return "\n".join(collected).strip()
    return ""


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """429/5xx 응답에 대한 대기 시간을 계산한다. Retry-After 헤더를 우선 존중."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), MAX_BACKOFF_SECONDS)
        except ValueError:
            pass
    return min(2.0**attempt, MAX_BACKOFF_SECONDS)


async def _ocr_image(client: httpx.AsyncClient, image: bytes) -> str:
    """이미지 1장을 Upstage OCR로 인식한다. 429/5xx는 백오프 후 재시도한다."""
    last_response: httpx.Response | None = None
    for attempt in range(settings.OCR_MAX_RETRIES):
        response = await client.post(
            UPSTAGE_OCR_URL,
            headers={"Authorization": f"Bearer {settings.UPSTAGE_API_KEY}"},
            files={"document": ("page.png", image, "image/png")},
            data={"model": "ocr"},
        )
        last_response = response
        if response.status_code == 429 or response.status_code >= 500:
            delay = _retry_delay(response, attempt)
            logger.warning(
                "Upstage OCR %d 응답 — %.1fs 후 재시도 (%d/%d)",
                response.status_code,
                delay,
                attempt + 1,
                settings.OCR_MAX_RETRIES,
            )
            await asyncio.sleep(delay)
            continue
        response.raise_for_status()
        return _parse_ocr_text(response.json())

    # 재시도 모두 소진 — 마지막 응답으로 예외를 발생시킨다.
    assert last_response is not None
    last_response.raise_for_status()
    return ""


async def ocr_pages(pdf_bytes: bytes, pages: list[PageText]) -> list[PageText]:
    """텍스트가 부족한 페이지를 OCR로 보강한 새 페이지 리스트를 반환한다."""
    if not settings.OCR_ENABLED or not settings.UPSTAGE_API_KEY:
        logger.info("OCR fallback 비활성화 또는 API 키 없음 — 원본 텍스트 유지")
        return pages

    sparse_pages = [p for p in pages if ExtractionService.is_page_sparse(p)]
    if not sparse_pages:
        return pages

    loop = asyncio.get_running_loop()
    ocr_text_by_page: dict[int, str] = {}
    request_delay = settings.OCR_REQUEST_DELAY_MS / 1000.0

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for index, page in enumerate(sparse_pages):
            # 레이트 리밋 완화를 위해 페이지 간 호출 간격을 둔다(첫 요청 제외).
            if index > 0 and request_delay > 0:
                await asyncio.sleep(request_delay)
            try:
                image = await loop.run_in_executor(
                    None, functools.partial(render_page_png, pdf_bytes, page.page_number)
                )
                text = await _ocr_image(client, image)
                if text:
                    ocr_text_by_page[page.page_number] = text
            except Exception:
                logger.exception("페이지 %d OCR 실패 — 원본 텍스트 유지", page.page_number)

    if not ocr_text_by_page:
        return pages

    return [
        PageText(
            page_number=p.page_number,
            text=ocr_text_by_page.get(p.page_number, p.text),
            has_images=p.has_images,
            drawing_count=p.drawing_count,
            source="ocr" if p.page_number in ocr_text_by_page else p.source,
        )
        for p in pages
    ]
