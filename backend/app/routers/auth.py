from fastapi import APIRouter

router = APIRouter()


@router.post("/register")
async def register():
    raise NotImplementedError


@router.post("/login")
async def login():
    raise NotImplementedError


@router.post("/logout")
async def logout():
    raise NotImplementedError
