"""앱 시작 시 Alembic 마이그레이션 실행."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def upgrade_head() -> None:
    root = Path(__file__).resolve().parents[2]
    logger.info("DB 마이그레이션 실행 중…")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        check=True,
    )
    logger.info("DB 마이그레이션 완료")
