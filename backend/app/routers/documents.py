from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def upload_document():
    """PDF 업로드 (type: lecture / past_exam)"""
    raise NotImplementedError


@router.get("")
async def list_documents():
    """문서 목록 (강의자료·족보 필터)"""
    raise NotImplementedError


@router.get("/{document_id}")
async def get_document(document_id: str):
    """문서 처리 상태 조회"""
    raise NotImplementedError


@router.get("/{document_id}/toc")
async def get_document_toc(document_id: str):
    """PDF 목차 조회 (시험 범위 선택용)"""
    raise NotImplementedError


@router.post("/{document_id}/search")
async def search_document(document_id: str):
    """RAG 검색 테스트"""
    raise NotImplementedError
