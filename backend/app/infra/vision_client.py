"""멀티모달 LLM 기반 페이지 이미지 이해.

그림/다이어그램이 포함된 강의 슬라이드 이미지를 입력받아, 검색·문제 생성에
바로 쓸 수 있는 본문 텍스트로 변환한다. 텍스트 전사뿐 아니라 다이어그램의
구성 요소와 관계(화살표, 흐름, 구조)를 서술하도록 지시한다.
"""

import base64

from app.config import settings
from app.infra.llm_client import openai_client

_PROMPT = (
    "다음은 대학 강의자료 PDF의 한 페이지(슬라이드) 이미지입니다. "
    "이 페이지를 검색과 시험 문제 생성에 사용할 수 있도록 본문 텍스트로 정리하세요.\n"
    "- 페이지에 있는 모든 글자(제목, 본문, 표, 라벨)를 빠짐없이 옮겨 적으세요.\n"
    "- 그림·다이어그램·흐름도가 있으면 구성 요소와 그 관계(연결, 화살표 방향, 순서, 계층 구조)를 "
    "문장으로 설명하세요.\n"
    "- 표는 행과 열의 의미가 드러나도록 정리하세요.\n"
    "- 해설이나 머리말 없이 페이지 내용 자체만 출력하세요. 페이지에 내용이 없으면 빈 문자열을 출력하세요."
)


def _model() -> str:
    return settings.VISION_MODEL or settings.LLM_MODEL


async def describe_page_image(png_bytes: bytes) -> str:
    """페이지 PNG 이미지를 멀티모달 LLM으로 설명한 본문 텍스트를 반환한다."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    response = await openai_client.chat.completions.create(
        model=_model(),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=1500,
        temperature=0.0,
    )
    return (response.choices[0].message.content or "").strip()
