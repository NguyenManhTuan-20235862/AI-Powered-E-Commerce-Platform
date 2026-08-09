"""Cấu hình Gunicorn cho production (task 2.1.2).

Chạy: gunicorn app.main:app -c gunicorn_conf.py
"""

import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"

# Công thức khuyến nghị chính thức của Gunicorn: (2 x số CPU) + 1 - đủ worker
# để 1 worker đang xử lý I/O (chờ MySQL/Mongo/Redis) không chặn worker khác,
# không quá nhiều để tránh tốn RAM/context-switch vô ích.
#
# CẢNH BÁO đã tự kiểm chứng lúc build task này: multiprocessing.cpu_count()
# TRONG container trả về số CPU của MÁY HOST/VM chạy Docker (không phải số CPU
# thực sự cấp cho container, trừ khi `docker run --cpus=N` giới hạn rõ) - trên
# máy dev nhiều core, công thức này tính ra 25 worker, hoàn toàn không hợp lý
# cho "dự án nhỏ". Vì vậy giới hạn trần _WORKERS_CAP để công thức không "chạy
# trốn" theo số core của máy build/host. Khi deploy lên server thật có cấu
# hình CPU cố định và biết trước, nên SET THẲNG biến môi trường GUNICORN_WORKERS
# thay vì dựa vào auto-detect này.
_WORKERS_CAP = 4
_default_workers = min((2 * multiprocessing.cpu_count()) + 1, _WORKERS_CAP)
workers = int(os.getenv("GUNICORN_WORKERS", _default_workers))

# timeout: worker không phản hồi (bị treo) quá N giây bị Gunicorn kill và spawn
# lại worker mới - 30s đủ rộng rãi cho request thường, không quá dài để giữ
# request treo (VD: query DB bị deadlock) chiếm worker vô thời hạn.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))

# graceful_timeout: khi Gunicorn nhận tín hiệu restart/shutdown (VD: deploy mới,
# SIGTERM từ Docker/orchestrator), worker có N giây để xử lý nốt request đang
# dang dở trước khi bị buộc kill - tránh cắt ngang request của user giữa chừng.
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

keepalive = 5

# Log ra thẳng stdout/stderr ("-") thay vì ghi file riêng trong container - để
# Docker/hệ thống ngoài container thu thập log (docker logs, driver logging của
# Docker, hoặc hệ thống tổng hợp log khi lên server thật). Xem giải thích về
# tương tác với app/core/logging.py trong summary trả lời task 2.1.2.
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
