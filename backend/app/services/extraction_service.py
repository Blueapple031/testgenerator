"""PyMuPDF(fitz) 기반 PDF 텍스트 추출.

텍스트 레이어가 거의 없는(스캔 이미지) 페이지는 OCR fallback 대상으로 판별한다.
fitz 호출은 동기·CPU 바운드이므로 워커에서 ``run_in_executor``로 감싸 호출한다.
"""

from dataclasses import dataclass

import fitz

# 페이지당 이 글자 수 미만이면 텍스트 레이어가 부족한 것으로 보고 OCR 후보로 본다.
MIN_CHARS_PER_PAGE = 20


@dataclass
class PageText:
    """추출된 페이지 단위 텍스트. page_number는 1-based."""

    page_number: int
    text: str


class ExtractionService:
    @staticmethod
    def extract_pages(pdf_bytes: bytes) -> tuple[list[PageText], int]:
        """PDF 바이트에서 페이지별 텍스트와 전체 페이지 수를 추출한다."""
        pages: list[PageText] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            page_count = doc.page_count
            for index, page in enumerate(doc):
                text = page.get_text("text").strip()
                pages.append(PageText(page_number=index + 1, text=text))
        return pages, page_count

    @staticmethod
    def is_page_sparse(page: PageText) -> bool:
        """해당 페이지가 OCR 대상(텍스트 부족)인지 여부."""
        return len(page.text) < MIN_CHARS_PER_PAGE

    @classmethod
    def needs_ocr(cls, pages: list[PageText]) -> bool:
        """문서 전체에 OCR fallback이 필요한지(텍스트가 부족한 페이지가 있는지) 판별한다."""
        return any(cls.is_page_sparse(page) for page in pages)
