from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session
from app.infra import minio_client
from app.infra.db_migrate import upgrade_head
from app.routers import auth, documents, exam_styles, exams, jobs, learning, pilot_admin, solve, workspaces
from app.services.pilot_account_service import PilotAccountService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_head()
    await minio_client.ensure_bucket()
    if settings.PILOT_AUTH_ENABLED and settings.PILOT_ACCOUNTS_SYNC_ON_STARTUP:
        path = Path(settings.PILOT_ACCOUNTS_PATH)
        if path.is_file():
            async with async_session() as db:
                result = await PilotAccountService.sync_from_yaml(db, path)
                logger.info(
                    "파일럿 계정 startup 동기화: created=%s updated=%s deactivated=%s",
                    result.created,
                    result.updated,
                    result.deactivated,
                )
        else:
            logger.warning("PILOT_ACCOUNTS_SYNC_ON_STARTUP=true 이지만 파일 없음: %s", path)
    yield


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
app.include_router(pilot_admin.router, prefix="/api/admin/pilot", tags=["pilot-admin"])
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
