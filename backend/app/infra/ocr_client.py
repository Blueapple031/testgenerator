"""Upstage OCR 기반 텍스트 추출 fallback.

PyMuPDF 텍스트 레이어가 부족한(스캔 이미지) 페이지만 이미지로 렌더링해
Upstage Document Digitization(OCR) API로 텍스트를 보강한다.

OCR가 비활성화돼 있거나 API 키가 없거나 호출이 실패하면
원본 페이지를 그대로 반환해 인덱싱 파이프라인이 중단되지 않게 한다.
"""

import asyncio
import functools
import logging

import fitz
import httpx

from app.config import settings
from app.services.extraction_service import ExtractionService, PageText

logger = logging.getLogger(__name__)

UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"
RENDER_DPI = 200
HTTP_TIMEOUT = 60.0


def _render_page_png(pdf_bytes: bytes, page_number: int) -> bytes:
    """지정한 페이지(1-based)를 PNG 바이트로 렌더링한다. (동기)"""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_number - 1]
        pixmap = page.get_pixmap(dpi=RENDER_DPI)
        return pixmap.tobytes("png")


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


async def _ocr_image(client: httpx.AsyncClient, image: bytes) -> str:
    response = await client.post(
        UPSTAGE_OCR_URL,
        headers={"Authorization": f"Bearer {settings.UPSTAGE_API_KEY}"},
        files={"document": ("page.png", image, "image/png")},
        data={"model": "ocr"},
    )
    response.raise_for_status()
    return _parse_ocr_text(response.json())


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

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for page in sparse_pages:
            try:
                image = await loop.run_in_executor(
                    None, functools.partial(_render_page_png, pdf_bytes, page.page_number)
                )
                text = await _ocr_image(client, image)
                if text:
                    ocr_text_by_page[page.page_number] = text
            except Exception:
                logger.exception("페이지 %d OCR 실패 — 원본 텍스트 유지", page.page_number)

    if not ocr_text_by_page:
        return pages

    return [
        PageText(page_number=p.page_number, text=ocr_text_by_page.get(p.page_number, p.text))
        for p in pages
    ]
