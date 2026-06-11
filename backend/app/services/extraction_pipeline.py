"""PDF 페이지 텍스트 보강 파이프라인 (Vision / OCR 순서 분기).

두 전략을 ``EXTRACTION_PIPELINE`` 환경변수로 전환해 A/B 비교할 수 있다.

- ``vision_first`` (기본): 그림 페이지 Vision → sparse 페이지 OCR
- ``ocr_first``: sparse 페이지 OCR → 여전히 sparse면 Vision
"""

from dataclasses import dataclass
from typing import Literal

from app.config import settings
from app.infra.ocr_client import ocr_pages
from app.services.extraction_service import ExtractionService, PageText, vision_filter_for_pipeline
from app.services.vision_service import enrich_pages_with_vision

ExtractionPipeline = Literal["vision_first", "ocr_first"]


@dataclass(frozen=True)
class EnrichmentStats:
    pipeline: ExtractionPipeline
    total_pages: int
    ocr_pages: int
    vision_pages: int

    @property
    def enriched_pages(self) -> int:
        """OCR 또는 Vision이 적용된 페이지 수(중복 제외는 호출 측에서 해석)."""
        return self.ocr_pages + self.vision_pages


async def enrich_pages(
    pdf_bytes: bytes,
    pages: list[PageText],
    *,
    pipeline: ExtractionPipeline | None = None,
) -> tuple[list[PageText], EnrichmentStats]:
    """설정된 파이프라인 순서로 OCR·Vision 보강을 적용한다."""
    mode: ExtractionPipeline = pipeline or settings.EXTRACTION_PIPELINE  # type: ignore[assignment]
    total = len(pages)
    ocr_count = 0
    vision_count = 0

    if mode == "ocr_first":
        if ExtractionService.needs_ocr(pages):
            pages, ocr_count = await ocr_pages(pdf_bytes, pages)
        pages, vision_count = await enrich_pages_with_vision(
            pdf_bytes,
            pages,
            page_filter=vision_filter_for_pipeline("ocr_first"),
        )
    else:
        pages, vision_count = await enrich_pages_with_vision(
            pdf_bytes,
            pages,
            page_filter=vision_filter_for_pipeline("vision_first"),
        )
        if ExtractionService.needs_ocr(pages):
            pages, ocr_count = await ocr_pages(pdf_bytes, pages)

    stats = EnrichmentStats(
        pipeline=mode,
        total_pages=total,
        ocr_pages=ocr_count,
        vision_pages=vision_count,
    )
    return pages, stats
