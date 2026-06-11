"""PyMuPDF(fitz) 기반 PDF 텍스트 추출 및 페이지 렌더링.

- 텍스트 레이어가 거의 없는(스캔 이미지) 페이지는 OCR fallback 대상으로 판별한다.
- 그림/다이어그램이 포함된 페이지는 vision 보강 대상으로 판별한다.

fitz 호출은 동기·CPU 바운드이므로 워커에서 ``run_in_executor``로 감싸 호출한다.
"""

from dataclasses import dataclass

import fitz

from app.config import settings

# 페이지당 "의미 있는 글자"(한글/영숫자) 수가 이 값 미만이면
# 텍스트 레이어가 부족한 것으로 보고 OCR 후보로 본다.
# 불릿(•)·공백·기호만 잔뜩 있는 슬라이드를 sparse로 정확히 잡기 위해
# 단순 길이가 아니라 의미 있는 글자 수를 기준으로 한다.
MIN_MEANINGFUL_CHARS = 10

# 페이지 렌더링 해상도(OCR·vision 공용).
RENDER_DPI = 200


@dataclass
class PageText:
    """추출된 페이지 단위 텍스트와 시각 요소 메타데이터. page_number는 1-based."""

    page_number: int
    text: str
    has_images: bool = False
    drawing_count: int = 0
    # 최종 텍스트를 만든 추출 방식: "text" | "ocr" | "vision"
    source: str = "text"


def render_page_png(pdf_bytes: bytes, page_number: int, dpi: int = RENDER_DPI) -> bytes:
    """지정한 페이지(1-based)를 PNG 바이트로 렌더링한다. (동기)"""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_number - 1]
        pixmap = page.get_pixmap(dpi=dpi)
        return pixmap.tobytes("png")


class ExtractionService:
    @staticmethod
    def extract_pages(pdf_bytes: bytes) -> tuple[list[PageText], int]:
        """PDF 바이트에서 페이지별 텍스트·시각 메타데이터와 전체 페이지 수를 추출한다."""
        pages: list[PageText] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            page_count = doc.page_count
            for index, page in enumerate(doc):
                text = page.get_text("text").strip()
                pages.append(
                    PageText(
                        page_number=index + 1,
                        text=text,
                        has_images=len(page.get_images(full=True)) > 0,
                        drawing_count=len(page.get_drawings()),
                    )
                )
        return pages, page_count

    @staticmethod
    def _meaningful_char_count(text: str) -> int:
        """한글·영숫자 등 실제 의미 있는 글자 수. 불릿·공백·기호는 제외한다."""
        return sum(1 for char in text if char.isalnum())

    @classmethod
    def is_page_sparse(cls, page: PageText) -> bool:
        """해당 페이지가 OCR 대상(의미 있는 텍스트 부족)인지 여부."""
        return cls._meaningful_char_count(page.text) < MIN_MEANINGFUL_CHARS

    @classmethod
    def needs_ocr(cls, pages: list[PageText]) -> bool:
        """문서 전체에 OCR fallback이 필요한지(텍스트가 부족한 페이지가 있는지) 판별한다."""
        return any(cls.is_page_sparse(page) for page in pages)

    @staticmethod
    def page_needs_vision(page: PageText) -> bool:
        """그림/다이어그램이 포함돼 멀티모달 설명이 필요한 페이지인지 판별한다."""
        return page.has_images or page.drawing_count >= settings.VISION_MIN_DRAWINGS
