"""EXTRACTION_PIPELINE 분기·Vision 대상 판별 단위 테스트."""

from app.services.extraction_service import PageText, vision_filter_for_pipeline


def _page(
    *,
    page_number: int = 1,
    text: str = "",
    has_images: bool = False,
    drawing_count: int = 0,
) -> PageText:
    return PageText(
        page_number=page_number,
        text=text,
        has_images=has_images,
        drawing_count=drawing_count,
    )


def test_vision_first_targets_diagram_pages_even_with_text():
    predicate = vision_filter_for_pipeline("vision_first")
    page = _page(text="프로세스와 스레드의 차이를 설명하라 " * 5, has_images=True)
    assert predicate(page) is True


def test_vision_first_skips_plain_text_page():
    predicate = vision_filter_for_pipeline("vision_first")
    page = _page(text="운영체제 개론 " * 10, has_images=False, drawing_count=0)
    assert predicate(page) is False


def test_ocr_first_vision_only_when_sparse():
    predicate = vision_filter_for_pipeline("ocr_first")
    sparse = _page(text="•", has_images=True)
    rich = _page(text="프로세스와 스레드 " * 10, has_images=True)
    assert predicate(sparse) is True
    assert predicate(rich) is False


def test_ocr_first_sparse_after_failed_ocr_still_targets_vision():
    predicate = vision_filter_for_pipeline("ocr_first")
    page = _page(text="---", has_images=False)
    assert predicate(page) is True
