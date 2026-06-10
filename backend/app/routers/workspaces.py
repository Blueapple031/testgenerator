from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_workspace():
    """워크스페이스 생성"""
    raise NotImplementedError


@router.get("")
async def list_workspaces():
    """워크스페이스 목록"""
    raise NotImplementedError


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """워크스페이스 상세 (문서·시험 포함)"""
    raise NotImplementedError
