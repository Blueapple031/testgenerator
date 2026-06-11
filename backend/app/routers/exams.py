from fastapi import APIRouter

router = APIRouter()


@router.get("/{exam_id}")
async def get_exam(exam_id: str):
    """전체 시험 JSON 조회"""
    raise NotImplementedError


@router.get("/{exam_id}/export")
async def export_exam_pdf(exam_id: str):
    """선택적 PDF보내기 (고도화). MVP는 웹 렌더링 + 브라우저 인쇄 사용."""
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


@router.post("/{exam_id}/export")
async def trigger_exam_export(exam_id: str):
    """편집 후 PDF보내기 재생성 (고도화, HTML 기반 export)"""
    raise NotImplementedError
