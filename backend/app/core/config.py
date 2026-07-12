import os
from dotenv import load_dotenv

# Load .env but DO NOT override existing environment variables
# Docker Compose sets DATABASE_URL, REDIS_URL etc. correctly via environment:
# Only load values that aren't already set
for env_path in ["/app/.env", ".env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
        break

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "RTIFN National & Diaspora Intelligence Platform (NDIP)"
    app_env: str = "development"
    database_url: str = "postgresql://agora_user:agora_pass@db:5432/agora_db"
    secret_key: str = "change-me-in-production-must-be-32-chars-min"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:3000"
    youtube_api_key: str = ""
    twitter_bearer_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "AgoraObservatory/1.0"
    news_api_key: str = ""
    meta_access_token: str = ""
    meta_page_ids: str = ""
    anthropic_api_key: str = ""

    class Config:
        env_file = (".env", "/app/.env")
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
