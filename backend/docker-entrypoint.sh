#!/bin/sh
# Entrypoint chung cho CẢ Dockerfile.dev VÀ Dockerfile.prod - áp dụng migration
# Alembic ĐÃ COMMIT (KHÔNG BAO GIỜ tự sinh migration mới) trước khi khởi động
# API server thật:
#
#   Backend container start
#           |
#   Wait MySQL healthy (docker-compose.yml, depends_on: condition: service_healthy)
#           |
#   alembic upgrade head   <-- entrypoint này
#           |
#   Start application server (uvicorn/gunicorn, CMD của từng Dockerfile)
#
# `set -e` - fail-fast THẬT: nếu "alembic upgrade head" thoát khác 0 (migration
# lỗi, mất kết nối MySQL...), script dừng NGAY tại đây, KHÔNG bao giờ chạy tới
# "exec "$@"" - container thoát với code lỗi thay vì khởi động server với
# schema có thể dở dang.
set -e

# CHỈ chạy migration khi container này đang khởi động API server thật
# (uvicorn/gunicorn) - `product-sync-scheduler` (docker-compose.yml, task
# 3.5.2) DÙNG LẠI Dockerfile.dev NÀY (chỉ override `command:` thành
# "python -m scripts.run_scheduler") - nếu chạy migration VÔ ĐIỀU KIỆN ở đây,
# `backend` VÀ `product-sync-scheduler` sẽ cùng áp dụng migration gần như
# đồng thời mỗi lần "docker compose up" (2 service không phụ thuộc thứ tự lẫn
# nhau, chỉ cùng chờ mysql/mongodb healthy) - đua nhau update `alembic_version`
# trên MySQL ngay TRONG topology hiện tại (không cần đợi tới lúc scale nhiều
# replica mới xảy ra, xem thêm docs/KNOWN_TODOS.md).
case "$1" in
  uvicorn|gunicorn)
    echo "[docker-entrypoint] Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "[docker-entrypoint] Migrations applied successfully."
    ;;
  *)
    echo "[docker-entrypoint] Command is '$1' (not uvicorn/gunicorn) - skipping migrations."
    ;;
esac

exec "$@"
