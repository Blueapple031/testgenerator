from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_job():
    """문제집 생성 Job 등록"""
    raise NotImplementedError


@router.get("/{job_id}")
async def get_job(job_id: str):
    """생성 상태 조회"""
    raise NotImplementedError


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE 기반 생성 진행 상태 스트리밍"""
    raise NotImplementedError
