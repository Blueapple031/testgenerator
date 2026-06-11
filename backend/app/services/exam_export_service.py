"""선택적 PDF보내기 (고도화).

MVP에서는 문제집의 정본은 JSON이며 웹 UI에서 렌더링한다.
사용자가 오프라인용 PDF가 필요하면 브라우저 인쇄(print stylesheet)를 사용한다.
장기 고도화 시 HTML 템플릿 → Playwright/Chromium 또는 WeasyPrint로 PDF를 생성할 수 있다.
"""


class ExamExportService:
    pass
