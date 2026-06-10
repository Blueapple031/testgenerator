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

    # LaTeX
    LATEX_BIN: str = "/usr/bin/xelatex"
    LATEX_FONT_PATH: str = "/usr/share/fonts/noto-cjk"

    # Limits
    EXAM_MAX_UPLOAD_BYTES: int = 52_428_800  # 50MB
    EXAM_CHUNK_SIZE: int = 800
    EXAM_CHUNK_OVERLAP: int = 120


settings = Settings()
