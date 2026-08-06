"""Cấu hình logging có cấu trúc (task 1.4.2).

Dùng `logging` chuẩn của Python, KHÔNG dùng structlog: project solo, quy mô
nhỏ, chưa có nhu cầu xuất log dạng JSON cho hệ thống tổng hợp log (ELK/
Datadog...). stdlib logging + 1 Formatter tùy biến + contextvar là đủ để có
timestamp/level/module/request_id trong mọi dòng log mà không cần thêm
dependency và API mới phải học. Khi nào cần structured JSON log thật (để ship
cho hệ thống ngoài), có thể đổi `Formatter` sang JSON mà không phải đổi kiến
trúc (setup_logging(), request_id_var, RequestIdFilter vẫn giữ nguyên).
"""

import logging
import logging.config
from contextvars import ContextVar
from pathlib import Path

from app.core.config import get_settings

# Context riêng cho từng request (async task) - middleware set giá trị này ở
# đầu request, mọi log phát sinh trong lúc xử lý request đó (kể cả trong
# exception handler) tự động có cùng request_id mà không cần truyền tay qua
# từng hàm. "-" là giá trị mặc định khi log phát sinh ngoài 1 request HTTP
# (VD: log lúc khởi động app).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"

# Rotate theo dung lượng (không theo ngày) - đơn giản, không phụ thuộc timezone
# server, đảm bảo file không phình to vô hạn: tối đa 5MB/file x 5 file cũ = 30MB.
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 5


class RequestIdFilter(logging.Filter):
    """Gắn request_id hiện tại (đọc từ contextvar) vào mọi log record.

    Gắn ở tầng Handler (không phải Logger) nên áp dụng cho MỌI logger đi qua
    handler đó (kể cả logger của uvicorn/sqlalchemy), tránh KeyError khi
    Formatter cần %(request_id)s mà record không có field này.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    """Gọi 1 lần lúc app khởi động (app/main.py) - cấu hình console (+ file
    handler khi KHÔNG phải production).

    Level: DEBUG khi dev, INFO khi production (đọc settings.is_production đã có
    sẵn từ app/core/config.py).

    Production (settings.is_production=True) CHỈ log ra console (stdout/stderr)
    - KHÔNG ghi file:
    - Gunicorn (Dockerfile.prod, gunicorn_conf.py) đã quy ước accesslog/errorlog
      ra stdout/stderr - container không được thiết kế để tự quản lý file log
      (Docker/orchestrator lo việc thu thập log qua stdout, đúng triết lý
      "12-factor app" - log là stream sự kiện, không phải file cục bộ).
    - Container production chạy bằng user KHÔNG PHẢI root (xem Dockerfile.prod)
      và KHÔNG có quyền ghi vào /app - nếu vẫn cố `LOG_DIR.mkdir()` + mở
      RotatingFileHandler như khi dev, toàn bộ Gunicorn worker crash ngay lúc
      khởi động với PermissionError (đã tự kiểm chứng lúc build task 2.1.2).
    """
    settings = get_settings()
    log_level = "INFO" if settings.is_production else "DEBUG"

    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
            "level": log_level,
        },
    }
    root_handlers = ["console"]

    if not settings.is_production:
        LOG_DIR.mkdir(exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filters": ["request_id"],
            "filename": str(LOG_FILE),
            "maxBytes": LOG_FILE_MAX_BYTES,
            "backupCount": LOG_FILE_BACKUP_COUNT,
            "encoding": "utf-8",
            "level": log_level,
        }
        root_handlers.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": RequestIdFilter},
            },
            "formatters": {
                "default": {"format": LOG_FORMAT, "datefmt": LOG_DATE_FORMAT},
            },
            "handlers": handlers,
            "root": {
                "level": log_level,
                "handlers": root_handlers,
            },
            "loggers": {
                # uvicorn.access bị tắt hẳn (handlers rỗng, không propagate) vì
                # RequestContextMiddleware đã tự log method/path/status/thời gian
                # xử lý cho MỌI request (item 3) - giữ cả 2 sẽ bị trùng dòng log.
                "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": False},
                # SQLAlchemy engine log rất ồn ở INFO/DEBUG (in ra từng câu SQL) -
                # chỉ hạ xuống DEBUG khi cần soi query thật, mặc định WARNING.
                "sqlalchemy.engine": {"level": "WARNING", "handlers": [], "propagate": True},
                # pymongo tự động heartbeat MongoDB mỗi ~10s (kể cả khi MongoDB
                # chưa chạy - module Mongo chưa tới task nào trong WBS), log DEBUG
                # rất ồn nếu không hạ level - chỉ hạ xuống DEBUG khi cần debug driver.
                "pymongo": {"level": "WARNING", "handlers": [], "propagate": True},
            },
        }
    )
