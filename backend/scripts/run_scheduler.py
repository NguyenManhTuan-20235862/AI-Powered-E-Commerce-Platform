"""Scheduler tiến trình ĐỘC LẬP (task 3.5.2) - chạy `sync_products_to_mongo()`
(task 3.5.1) theo lịch cron, KHÔNG nhúng trong tiến trình FastAPI.

## Vì sao KHÔNG nhúng APScheduler trong app/main.py

Production chạy Gunicorn với NHIỀU Uvicorn worker (`gunicorn_conf.py`,
`_WORKERS_CAP` - task 2.1.2). Nếu APScheduler chạy TRONG process app
FastAPI, MỖI worker (process riêng biệt do Gunicorn fork ra) sẽ tự khởi tạo
1 bản lịch RIÊNG - tới giờ, N worker cùng chạy job → sync N lần liên tiếp
cùng 1 dữ liệu (không sai dữ liệu cuối cùng vì `sync_products_to_mongo()`
idempotent, nhưng lãng phí tài nguyên N lần vô ích + log nhiễu N dòng giống
hệt nhau).

Đã cân nhắc 2 hướng (đã xác nhận với người dùng, chọn hướng b):
- **(a) Vẫn nhúng trong app**, thêm cơ chế chỉ cho 1 worker "được phép" chạy
  (file lock, hoặc gán số thứ tự qua hook `post_fork` của Gunicorn). Nhược
  điểm: (1) là 1 lớp workaround thêm vào, không giải quyết tận gốc - phải tự
  viết + bảo trì logic bầu chọn "worker chính"; (2) `Dockerfile.dev` (dev,
  `uvicorn --reload`, LUÔN chỉ 1 process) không có vấn đề N-worker này -
  nghĩa là logic bầu chọn chỉ thật sự cần ở PROD, thêm 1 nhánh hành vi
  dev-vs-prod phải tự nhớ test riêng; (3) nếu sau này scale ngang (nhiều
  CONTAINER Backend, không chỉ nhiều worker trong 1 container) - lock theo
  file (chỉ thấy được trong 1 container) KHÔNG còn đủ, mỗi container lại tự
  bầu ra 1 "worker chính" riêng → vẫn chạy trùng ở cấp container.
- **(b) Tách hẳn 1 service/container riêng** (ĐÃ CHỌN - xem `docker-compose.yml`
  service `product-sync-scheduler`) - CHỈ chạy scheduler, KHÔNG chạy
  Gunicorn/API, độc lập HOÀN TOÀN với số lượng worker của Backend (dù
  Backend chạy 1 worker hay 4, hay sau này scale ngang bao nhiêu container -
  vẫn CHỈ CÓ ĐÚNG 1 container `product-sync-scheduler`, không cần logic bầu
  chọn/khóa nào cả - đúng cấu trúc, không phải workaround). Đánh đổi: thêm 1
  service trong `docker-compose.yml` (chấp nhận được - project đã có 5
  service, quy mô đồ án solo, chi phí tài nguyên thêm không đáng kể).

## Lịch chạy

Mặc định 2h sáng hàng ngày, **giờ Việt Nam** (`Asia/Ho_Chi_Minh`, KHÔNG phải
UTC - "2h sáng ít traffic" là giờ địa phương thật, dùng UTC sẽ lệch 7 tiếng,
chạy nhầm vào 9h sáng giờ Việt Nam). Đọc `settings.PRODUCT_SYNC_CRON` (cú
pháp cron chuẩn, `app/core/config.py`) qua biến môi trường - TEST được lịch
chạy sau 1-2 phút mà KHÔNG cần sửa code (VD đặt `PRODUCT_SYNC_CRON=*/2 * * * *`
trong `backend/.env` lúc verify, đổi lại `0 2 * * *` sau khi xong).

## Lỗi trong lúc sync KHÔNG được làm crash scheduler

Bọc try/except quanh MỖI lần chạy job (`_run_sync_job`) - MySQL/MongoDB tạm
thời không kết nối được, hay bất kỳ lỗi nào khác từ `sync_products_to_mongo()`,
chỉ log lỗi (kèm traceback) rồi tiếp tục. APScheduler tự động chờ tới lần
chạy kế tiếp theo lịch, KHÔNG hủy job định kỳ chỉ vì 1 lần chạy lỗi.

## Lịch KHÔNG "mất" sau khi container restart

Không phải nhờ cơ chế lưu trữ đặc biệt nào - APScheduler ở đây dùng jobstore
mặc định (trong bộ nhớ, KHÔNG persist) CỐ TÌNH, vì lịch chạy được KHAI BÁO
LẠI TỪ ĐẦU (đọc `settings.PRODUCT_SYNC_CRON`) mỗi khi `main()` chạy - restart
container chỉ đơn giản là chạy lại `main()`, tự nhiên đăng ký lại ĐÚNG lịch
cũ (nguồn sự thật là code/biến môi trường, không phải state runtime nào cần
"nhớ lại"). Không cần jobstore lưu trữ bền (VD `SQLAlchemyJobStore`) vì
không có nhu cầu thêm/xóa job động lúc runtime qua API - job DUY NHẤT của
scheduler này cố định, biết trước từ lúc code.

## Trigger chạy tay (verify/test) - KHÔNG qua HTTP endpoint

Dùng THẲNG script gốc (task 3.5.1, vẫn giữ nguyên `if __name__ ==
"__main__":`) - KHÔNG thêm endpoint HTTP `Admin`-only cho việc này (đã cân
nhắc): endpoint kiểu vậy nằm NGOÀI `docs/API_SPEC.md` (spec hiện không có
mục nào cho "trigger job nội bộ"), và chạy job (query MySQL + ghi nhiều
document Mongo, tỷ lệ thuận số sản phẩm) BÊN TRONG 1 HTTP request sẽ chiếm
dụng 1 Gunicorn worker suốt thời gian chạy - đi ngược đúng lý do chọn tách
container riêng ở trên (dự án CHƯA có traffic thật nên rủi ro này chưa lộ rõ,
nhưng thêm 1 endpoint mang sẵn rủi ro đó là quyết định kiến trúc không đáng
đánh đổi cho lợi ích nhỏ "tiện tay hơn docker exec 1 chút"). Cách chạy tay:
    docker compose exec product-sync-scheduler python -m scripts.sync_products_to_mongo
(hoặc `docker compose exec backend ...` - cùng image/code, chạy ở đâu cũng
ra kết quả giống nhau).
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logging import setup_logging
from scripts.sync_products_to_mongo import sync_products_to_mongo

logger = logging.getLogger(__name__)

VIETNAM_TZ = "Asia/Ho_Chi_Minh"


def _run_sync_job() -> None:
    logger.info("Bắt đầu chạy job đồng bộ product_catalog_sync (theo lịch)")
    try:
        sync_products_to_mongo()
    except Exception:
        logger.error(
            "Job đồng bộ product_catalog_sync THẤT BẠI - chờ lịch chạy kế tiếp, không dừng scheduler",
            exc_info=True,
        )
    else:
        logger.info("Job đồng bộ product_catalog_sync HOÀN TẤT")


def main() -> None:
    setup_logging()
    settings = get_settings()

    scheduler = BlockingScheduler(timezone=VIETNAM_TZ)
    scheduler.add_job(
        _run_sync_job,
        trigger=CronTrigger.from_crontab(settings.PRODUCT_SYNC_CRON, timezone=VIETNAM_TZ),
        id="sync_products_to_mongo",
        # coalesce=True - nếu scheduler bị dừng lâu (VD container restart)
        # và bỏ lỡ nhiều lần chạy trong lúc đó, chỉ chạy bù ĐÚNG 1 LẦN khi
        # quay lại (không dồn chạy N lần liên tiếp cho N lần lỡ hẹn).
        coalesce=True,
        # misfire_grace_time=3600 - nếu container khởi động lại đúng lúc gần
        # giờ chạy đã lỡ, vẫn cho chạy bù nếu còn trong khung 1 giờ - quá
        # khung thì bỏ qua, đợi lần kế tiếp (tránh chạy bù 1 job đã lỡ quá
        # lâu, không còn ý nghĩa "chạy đúng giờ ít traffic" nữa).
        misfire_grace_time=3600,
    )

    logger.info(
        "Scheduler khởi động - lịch chạy: '%s' (cron, giờ %s)",
        settings.PRODUCT_SYNC_CRON,
        VIETNAM_TZ,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
