import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "News API"
    API_VERSION: str = "v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./news.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "1892dhianiandowqd0n")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "xxx")
    ALLOWED_ORIGINS: list = ["http://localhost:8080", "http://localhost:3000"]
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()