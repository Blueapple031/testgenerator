from fastapi import APIRouter

router = APIRouter()


@router.get("/weak-concepts")
async def get_weak_concepts():
    """취약 개념 조회"""
    raise NotImplementedError


@router.get("/mastery")
async def get_mastery():
    """사용자 개념별 숙련도 조회"""
    raise NotImplementedError


@router.get("/recommendations")
async def get_recommendations():
    """KT 기반 개인화 복습·문제 추천"""
    raise NotImplementedError
