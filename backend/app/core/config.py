"""Cấu hình ứng dụng, đọc từ biến môi trường (.env) bằng Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI-Powered E-Commerce Platform API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # MySQL (SQLAlchemy) - dùng cho Auth, Product, Order, Cart
    DATABASE_URL: str

    # MongoDB - dùng cho Chat log, Review
    MONGO_URI: str
    MONGO_DB_NAME: str = "ecommerce_mongo"

    # Redis - cache, session, rate limit...
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Agent (LangChain)
    OPENAI_API_KEY: str | None = None

    @property
    def is_production(self) -> bool:
        """True khi APP_ENV=production - dùng để ẩn Swagger/ReDoc docs."""
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Trả về instance Settings dùng chung (cache để không đọc lại .env nhiều lần)."""
    return Settings()
