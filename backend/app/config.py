from typing import Callable, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ExtractionPipelineMode = Literal["vision_first", "ocr_first"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dontdelay:dontdelay@postgres:5432/dontdelay"

    # MinIO
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "dontdelay-exam"

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Embedding
    EMBEDDING_PROVIDER: str = "openai"  # "local" | "openai"
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # OCR
    OCR_ENABLED: bool = True
    UPSTAGE_API_KEY: str = ""
    OCR_MAX_RETRIES: int = 5  # 429/5xx 재시도 횟수
    OCR_REQUEST_DELAY_MS: int = 600  # 페이지 간 호출 간격(레이트 리밋 완화)

    # Vision (그림/다이어그램 포함 페이지를 멀티모달 LLM으로 설명)
    VISION_ENABLED: bool = True
    VISION_MODEL: str = ""  # 비우면 LLM_MODEL을 사용
    VISION_MIN_DRAWINGS: int = 10  # 벡터 드로잉이 이 수 이상이면 다이어그램으로 보고 vision 적용
    VISION_REQUEST_DELAY_MS: int = 300  # 페이지 간 vision 호출 간격

    # PDF 텍스트 보강 순서: vision_first | ocr_first (A/B 비교용)
    EXTRACTION_PIPELINE: ExtractionPipelineMode = "vision_first"

    # RAG
    RAG_DEFAULT_TOP_K: int = 10
    RAG_MAX_TOP_K: int = 30
    EXAM_GEN_RAG_TOP_K: int = 12  # 문제 생성 시 LLM에 전달할 chunk 수

    # Exam generation pipeline (dedup / candidate-based)
    EXAM_GEN_CANDIDATE_MULTIPLIER: int = 2
    EXAM_GEN_MIN_CANDIDATE_COUNT: int = 12
    EXAM_GEN_MAX_RETRIES: int = 3
    EXAM_GEN_STEM_SIMILARITY_THRESHOLD: float = 0.85
    EXAM_GEN_CONCEPT_SIMILARITY_THRESHOLD: float = 0.88
    EXAM_GEN_BASE_TEMPERATURE: float = 0.7
    EXAM_GEN_RETRY_TEMPERATURE: float = 0.9
    EXAM_GEN_MAX_CONTEXT_CHUNKS: int = 3
    EXAM_GEN_STEM_FALLBACK_RATIO: float = 0.85  # difflib fallback when embedding unavailable
    EXAM_GEN_ESSAY_SHORT_MIN_ANSWER_LEN: int = 80
    EXAM_GEN_ESSAY_LONG_MIN_ANSWER_LEN: int = 150
    EXAM_GEN_OUTLINE_COVERAGE_RATIO: float = 0.5

    # Exam generation
    EXAM_MAX_QUESTION_COUNT: int = 30
    EXAM_GEN_FULL_CONTEXT_MAX_CHARS: int = 120_000  # FULL_CONTEXT 프롬프트 상한

    # Exam style (족보) analysis
    EXAM_STYLE_MAX_TEXT_CHARS: int = 32_000

    # Limits
    EXAM_MAX_UPLOAD_BYTES: int = 52_428_800  # 50MB
    EXAM_CHUNK_SIZE: int = 800
    EXAM_CHUNK_OVERLAP: int = 120


settings = Settings()
