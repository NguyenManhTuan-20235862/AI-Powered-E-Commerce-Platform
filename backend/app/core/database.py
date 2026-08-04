"""Kết nối tới MySQL (SQLAlchemy), MongoDB (pymongo) và Redis.

Cung cấp các dependency (get_db, get_mongo_db, get_redis) để inject vào router/service.
"""

from collections.abc import Generator

import redis
from pymongo import MongoClient
from pymongo.database import Database as MongoDatabase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# ---- MySQL (SQLAlchemy) ----
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: cấp một SQLAlchemy Session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- MongoDB ----
mongo_client: MongoClient = MongoClient(settings.MONGO_URI)


def get_mongo_db() -> MongoDatabase:
    """FastAPI dependency: trả về database MongoDB dùng chung."""
    return mongo_client[settings.MONGO_DB_NAME]


# ---- Redis ----
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> redis.Redis:
    """FastAPI dependency: trả về Redis client dùng chung."""
    return redis_client
