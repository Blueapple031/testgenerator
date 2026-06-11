from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.infra import minio_client
from app.routers import auth, documents, exam_styles, exams, jobs, learning, solve, workspaces


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MinIO 버킷 초기화 (없으면 생성)
    await minio_client.ensure_bucket()
    # TODO: 임베딩 모델 로딩 등 추가 startup 로직
    yield
    # shutdown


app = FastAPI(
    title="DontDelay API",
    description="AI 기반 시험 문제 생성 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(exam_styles.router, prefix="/api/exam-styles", tags=["exam-styles"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(solve.router, prefix="/api/exams", tags=["solve"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
