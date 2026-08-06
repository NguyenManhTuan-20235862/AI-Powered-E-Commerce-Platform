"""Kết nối tới MySQL (SQLAlchemy), MongoDB (pymongo) và Redis.

Cung cấp các dependency (get_db, get_mongo_db, get_redis) để inject vào router/service.
"""

from collections.abc import Generator

import redis
from pymongo import MongoClient
from pymongo.database import Database as MongoDatabase
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class dùng chung cho toàn bộ SQLAlchemy models (MySQL).

    Alembic (`alembic/env.py`) import `Base.metadata` từ đây để autogenerate migration.
    """


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
# pymongo (sync), KHÔNG dùng motor (async) - quyết định tường minh ở task 3.2.3
# (đã hỏi lại, không suy đoán): TOÀN BỘ router hiện tại trong repo là `def`
# (sync) - ngoại trừ đúng 1 chỗ WebSocket /ws/chat (FastAPI bắt buộc async cho
# WebSocket) - dùng motor sẽ buộc mọi router có đọc/ghi Mongo (2 GET trong
# ai_chat.py, 3 endpoint trong review.py, task 6.x) phải đổi sang `async def`,
# lệch khỏi convention sync 100% hiện tại, thêm 1 dependency mới ngoài
# requirements-core.txt/CLAUDE.md đã ghi, và thêm độ phức tạp test
# (pytest-asyncio) không tương xứng lợi ích ở quy mô đồ án solo. Hệ quả cần
# nhớ: WebSocket /ws/chat (task 5.1, async bắt buộc) khi gọi client Mongo sync
# này PHẢI bọc qua `asyncio.to_thread(...)` (KHÔNG gọi `collection.insert_one()`
# trực tiếp trong hàm async) - gọi trực tiếp sẽ block event loop, ảnh hưởng mọi
# WebSocket connection khác đang chạy chung 1 process.
#
# MongoClient tự quản lý connection pool (mặc định maxPoolSize=100) VÀ tự
# thread-safe - tạo 1 instance module-level dùng chung cho toàn app (giống
# `engine`/`redis_client` bên dưới), KHÔNG tạo mới mỗi request. Constructor
# KHÔNG kết nối ngay (lazy - chỉ thật sự mở socket ở lần gọi operation đầu
# tiên) - endpoint /health (app/main.py) gọi `admin.command("ping")` để verify
# kết nối thật, không chỉ dựa vào việc khởi tạo client không lỗi.
# serverSelectionTimeoutMS=3000 (mặc định PyMongo là 30000/30s) - 30s mặc định
# QUÁ DÀI cho 1 API web (client/health check không nên treo 30s chờ Mongo nếu
# nó đang down) - 3s đủ ngắn để /health (app/main.py) phản hồi nhanh trong
# khoảng timeout 5s mà Docker healthcheck cho phép (docker-compose.yml), vẫn
# đủ dài để không báo lỗi nhầm do độ trễ mạng thoáng qua bình thường.
mongo_client: MongoClient = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)


def get_mongo_db() -> MongoDatabase:
    """FastAPI dependency: trả về database MongoDB dùng chung.

    Tên database lấy từ `settings.MONGO_DB_NAME` (biến riêng, mặc định
    `ecommerce_mongo`) - KHÔNG lấy từ path trong `MONGO_URI` (URI hiện tại chỉ
    có `/?authSource=admin`, không có tên DB - đúng theo TODO #7 đã xử lý,
    `authSource=admin` là DB xác thực user root, KHÁC với DB chứa dữ liệu
    thật `chat_logs`/`reviews`).
    """
    return mongo_client[settings.MONGO_DB_NAME]


# ---- Redis ----
# redis-py (sync) - cùng quyết định/lý do với pymongo (sync) ở task 3.2.3 (xem
# comment MongoDB phía trên): toàn bộ router hiện tại là `def` (sync), dùng
# client async (VD aioredis/redis.asyncio) sẽ buộc mọi router có dùng cache
# (task 3.3.1 trở đi) phải đổi sang `async def`, lệch convention hiện tại.
# WebSocket /ws/chat (task 5.1, async bắt buộc) khi cần đọc/ghi Redis (VD rate
# limit AI chat, task 8.3) qua client sync này PHẢI bọc `asyncio.to_thread(...)`
# giống lưu ý đã ghi cho MongoDB - KHÔNG gọi trực tiếp trong hàm async.
#
# socket_connect_timeout/socket_timeout=3 (giây) - redis-py mặc định KHÔNG có
# timeout nào cả (None = chờ vô hạn nếu Redis không phản hồi) - còn tệ hơn
# default 30s của PyMongo (serverSelectionTimeoutMS ở mongo_client phía trên).
# 3s cùng ngưỡng đã chọn cho MongoDB, đủ ngắn để request không treo vô hạn khi
# Redis down, đủ dài để không báo lỗi nhầm do độ trễ mạng thoáng qua.
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def get_redis() -> redis.Redis:
    """FastAPI dependency: trả về Redis client dùng chung."""
    return redis_client
