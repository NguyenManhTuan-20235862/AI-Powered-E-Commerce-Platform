"""Tạo index thật cho các collection MongoDB (task 3.2.3) — index đã THIẾT KẾ
(chưa tạo) ở task 3.2.1 (`chat_logs`) và 3.2.2 (`reviews`), xem
`docs/DATABASE_SCHEMA.md` mục "MongoDB Collections" cho lý do chọn từng index.

Script RIÊNG (không tự chạy lúc app startup) - cùng triết lý với Alembic
migration (MySQL): tạo index là 1 THAO TÁC SCHEMA tường minh, chạy khi cần
(sau khi deploy/đổi thiết kế index), KHÔNG chạy ngầm mỗi lần app khởi động
(main.py không import/gọi file này) - tránh app chậm khởi động hoặc âm thầm
build lại index mỗi lần restart container dev (`--reload` khởi động lại rất
thường xuyên lúc code).

Idempotent: `create_index()` của PyMongo là no-op nếu index CÙNG key pattern +
CÙNG option (kể cả `name`) đã tồn tại - chạy lại nhiều lần AN TOÀN, không tạo
trùng. Lưu ý: nếu sau này đổi field/option của 1 index nhưng GIỮ NGUYÊN
`name`, MongoDB sẽ báo lỗi "IndexOptionsConflict" thay vì âm thầm ghi đè - đây
là hành vi ĐÚNG mong muốn (báo lỗi rõ ràng thay vì có 2 định nghĩa khác nhau
cho cùng 1 tên) - nếu cố tình đổi thiết kế index, phải tự cân nhắc đổi cả
`name` hoặc drop index cũ trước.

Không thêm `try/except` bọc quanh `create_index()` - lỗi kết nối/lỗi
IndexOptionsConflict thật SỰ NÊN crash script rõ ràng (in traceback), không
nuốt lỗi rồi báo "thành công" sai sự thật.

Cách chạy (giống `scripts/seed_admin.py`) - trong container backend dev:
    docker compose exec backend python -m scripts.create_mongo_indexes
"""

from pymongo import ASCENDING

from app.core.database import get_mongo_db


def create_mongo_indexes() -> None:
    db = get_mongo_db()

    # Hướng ASCENDING/DESCENDING không ảnh hưởng hiệu năng cho field SORT
    # DUY NHẤT ở cuối 1 compound index (MongoDB quét index theo cả 2 chiều
    # được) - chọn ASCENDING đồng nhất cho dễ đọc, không phải quyết định UX
    # "mới nhất trước hay cũ nhất trước" (task 5.1/6.x quyết định lúc viết
    # query thật, không phụ thuộc hướng index).
    chat_logs = db["chat_logs"]
    chat_logs.create_index(
        [("user_id", ASCENDING), ("created_at", ASCENDING)],
        name="ix_chat_logs_user_id_created_at",
    )
    chat_logs.create_index(
        [("session_id", ASCENDING), ("created_at", ASCENDING)],
        name="ix_chat_logs_session_id_created_at",
    )
    chat_logs.create_index(
        [("created_at", ASCENDING)],
        name="ix_chat_logs_created_at",
    )

    reviews = db["reviews"]
    # Thứ tự field theo nguyên tắc ESR (Equality, Sort, Range) đã chốt ở
    # docs/DATABASE_SCHEMA.md: product_id + is_deleted là điều kiện equality
    # trong query thật (GET /products/{id}/reviews luôn lọc đúng 2 field này),
    # created_at là field dùng để sort - đặt sau 2 field equality.
    reviews.create_index(
        [("product_id", ASCENDING), ("is_deleted", ASCENDING), ("created_at", ASCENDING)],
        name="ix_reviews_product_id_is_deleted_created_at",
    )
    reviews.create_index(
        [("user_id", ASCENDING), ("order_id", ASCENDING), ("product_id", ASCENDING)],
        name="uq_reviews_user_id_order_id_product_id",
        unique=True,
    )

    print(f"chat_logs - index hiện có: {sorted(chat_logs.index_information().keys())}")
    print(f"reviews   - index hiện có: {sorted(reviews.index_information().keys())}")


if __name__ == "__main__":
    create_mongo_indexes()
