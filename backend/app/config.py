from pydantic_settings import BaseSettings, SettingsConfigDict


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
    LLM_MODEL: str = "gpt-4o"

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
    VISION_MODEL: str = ""  # 비우면 LLM_MODEL(gpt-4o)을 사용
    VISION_MIN_DRAWINGS: int = 10  # 벡터 드로잉이 이 수 이상이면 다이어그램으로 보고 vision 적용
    VISION_REQUEST_DELAY_MS: int = 300  # 페이지 간 vision 호출 간격

    # RAG
    RAG_DEFAULT_TOP_K: int = 10
    RAG_MAX_TOP_K: int = 30
    EXAM_GEN_RAG_TOP_K: int = 12  # 문제 생성 시 LLM에 전달할 chunk 수

    # Exam generation
    EXAM_MAX_QUESTION_COUNT: int = 30

    # Limits
    EXAM_MAX_UPLOAD_BYTES: int = 52_428_800  # 50MB
    EXAM_CHUNK_SIZE: int = 800
    EXAM_CHUNK_OVERLAP: int = 120


settings = Settings()
