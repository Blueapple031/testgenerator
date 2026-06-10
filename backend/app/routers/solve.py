from fastapi import APIRouter

router = APIRouter()


@router.post("/{exam_id}/answers")
async def submit_answers(exam_id: str):
    """풀이 결과 제출 (풀이 시간 포함)"""
    raise NotImplementedError


@router.post("/{exam_id}/interactions")
async def log_interactions(exam_id: str):
    """풀이 이벤트 로그 저장 (시작, 제출, 힌트, 답 변경, 이탈)"""
    raise NotImplementedError
