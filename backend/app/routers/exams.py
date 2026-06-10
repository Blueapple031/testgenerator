from fastapi import APIRouter

router = APIRouter()


@router.get("/{exam_id}")
async def get_exam(exam_id: str):
    """전체 시험 JSON 조회"""
    raise NotImplementedError


@router.get("/{exam_id}/download")
async def download_exam_pdf(exam_id: str):
    """PDF 다운로드"""
    raise NotImplementedError


@router.patch("/{exam_id}/questions/{question_id}")
async def update_question(exam_id: str, question_id: str):
    """개별 문제 수정"""
    raise NotImplementedError


@router.post("/{exam_id}/questions/{question_id}/regenerate")
async def regenerate_question(exam_id: str, question_id: str):
    """개별 문제 재생성"""
    raise NotImplementedError


@router.delete("/{exam_id}/questions/{question_id}")
async def delete_question(exam_id: str, question_id: str):
    """문제 삭제"""
    raise NotImplementedError


@router.post("/{exam_id}/rebuild-pdf")
async def rebuild_pdf(exam_id: str):
    """편집 후 PDF 재생성"""
    raise NotImplementedError
