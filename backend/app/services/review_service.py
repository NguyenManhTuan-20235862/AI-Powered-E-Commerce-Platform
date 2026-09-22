"""Business logic: Review (MongoDB collection `reviews`, task "Hoàn thiện
review sản phẩm") - tách khỏi router app/routers/review.py, cùng convention
product_service.py/chat_service.py.

Đây là hàm repository DÙNG CHUNG đã note ở docs/KNOWN_TODOS.md #12 -
`list_product_reviews()` là NƠI DUY NHẤT filter `is_deleted: False` cho đọc
công khai, router/endpoint khác KHÔNG tự `mongo_db["reviews"].find(...)` trực
tiếp.

Index (unique `(user_id, order_id, product_id)` + compound
`(product_id, is_deleted, created_at)`) KHÔNG tạo ở file này - đã có SẴN từ
task 3.2.3 (`backend/scripts/create_mongo_indexes.py`, chạy tay 1 lần, đã
chạy thật trên MongoDB dev - phát hiện lúc verify task này, tự kiểm bằng
`mongosh` thấy `ix_reviews_product_id_is_deleted_created_at`/
`uq_reviews_user_id_order_id_product_id` đã tồn tại kèm ~63 review demo, xem
`backend/scripts/seed_demo_orders_reviews.py`) - KHÔNG tạo lại ở đây (main.py
KHÔNG tự tạo index lúc khởi động, đúng quyết định đã ghi trong docstring
script đó: index là thao tác schema tường minh, không chạy ngầm mỗi lần
restart). `tests/conftest.py` gọi lại ĐÚNG hàm trong script đó cho DB test.
"""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database as MongoDatabase
from pymongo.errors import DuplicateKeyError
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.review import ReviewAdminRead, ReviewRead

REVIEWS_COLLECTION = "reviews"


class ReviewError(Exception):
    """Lỗi nghiệp vụ Review (chưa mua/chưa giao/sai đơn) - router dịch sang
    HTTPException 400, cùng convention `CartError`."""


class DuplicateReviewError(ReviewError):
    """Vi phạm unique index `(user_id, order_id, product_id)` - user đã review
    đúng sản phẩm này từ đúng đơn hàng này rồi - router dịch sang 409."""


def verify_purchase(db: Session, *, user_id: int, order_id: int, product_id: int) -> Order:
    """Xác nhận `order_id` THUỘC ĐÚNG `user_id`, chứa ĐÚNG `product_id`, và
    đơn đã `delivered` - raise `ReviewError` với message CỤ THỂ cho từng lý do
    sai (KHÔNG gộp chung 1 message mơ hồ như `_unauthorized()` ở
    `security.py` - đây KHÔNG phải bối cảnh bảo mật nhạy cảm dò hệ thống, user
    có QUYỀN biết chính xác vì sao chưa review được để họ tự sửa, VD lỡ chọn
    nhầm đơn hàng)."""
    order = db.get(Order, order_id)
    if order is None or order.user_id != user_id:
        raise ReviewError("Không tìm thấy đơn hàng này của bạn")
    if order.status != OrderStatus.delivered:
        raise ReviewError("Chỉ có thể đánh giá sau khi đơn hàng đã giao thành công")

    has_product = (
        db.query(OrderItem.id)
        .filter(OrderItem.order_id == order_id, OrderItem.product_id == product_id)
        .first()
        is not None
    )
    if not has_product:
        raise ReviewError("Đơn hàng này không chứa sản phẩm bạn đang đánh giá")

    return order


def create_review(
    mongo_db: MongoDatabase,
    *,
    product_id: int,
    user_id: int,
    user_name: str,
    order_id: int,
    rating: int,
    comment: str | None,
    images: list[str] | None,
) -> ReviewRead:
    """Insert 1 review - `created_at` set Ở ĐÂY (service layer), KHÔNG tin
    giá trị client gửi lên (nếu có) - cùng convention `chat_service.py:save_chat_log()`."""
    document = {
        "product_id": product_id,
        "user_id": user_id,
        "user_name": user_name,
        "order_id": order_id,
        "rating": rating,
        "comment": comment,
        "images": images,
        "is_verified_purchase": True,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }
    try:
        result = mongo_db[REVIEWS_COLLECTION].insert_one(document)
    except DuplicateKeyError as exc:
        raise DuplicateReviewError("Bạn đã đánh giá sản phẩm này từ đơn hàng này rồi") from exc

    document["_id"] = result.inserted_id
    return ReviewRead.model_validate(document)


def list_product_reviews(
    mongo_db: MongoDatabase, *, product_id: int, page: int, page_size: int
) -> tuple[list[ReviewRead], int, float | None]:
    """Danh sách review CÔNG KHAI của 1 sản phẩm - LUÔN filter `is_deleted:
    False` (xem docs/KNOWN_TODOS.md #12 - đây LÀ hàm dùng chung duy nhất cho
    việc này). `average_rating` tính trên TOÀN BỘ review khớp filter (KHÔNG
    chỉ trang hiện tại) qua 1 aggregation `$group` riêng, tách khỏi query
    phân trang (2 query đơn giản, dễ đọc hơn 1 pipeline `$facet` gộp - quy mô
    dữ liệu đồ án không cần tối ưu số round-trip tới mức đó)."""
    collection = mongo_db[REVIEWS_COLLECTION]
    query_filter = {"product_id": product_id, "is_deleted": False}

    total = collection.count_documents(query_filter)
    docs = collection.find(query_filter).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [ReviewRead.model_validate(doc) for doc in docs]

    average_rating: float | None = None
    if total > 0:
        agg = list(
            collection.aggregate(
                [{"$match": query_filter}, {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}]
            )
        )
        if agg:
            average_rating = round(agg[0]["avg"], 1)

    return items, total, average_rating


def soft_delete_review(mongo_db: MongoDatabase, review_id: str) -> bool:
    """Soft-delete (Admin) - trả `False` nếu `review_id` không đúng định dạng
    ObjectId HOẶC không tìm thấy document CHƯA bị xóa (router tự raise 404).
    Idempotent về mặt DỮ LIỆU (gọi lại trên review ĐÃ xóa không đổi gì thêm,
    không lỗi 500) nhưng KHÔNG idempotent về mặt HTTP response (404 ở lần
    gọi thứ 2 - đúng ngữ nghĩa REST, tài nguyên "đã xóa" không còn để xóa lại)."""
    try:
        object_id = ObjectId(review_id)
    except (InvalidId, TypeError):
        return False

    result = mongo_db[REVIEWS_COLLECTION].update_one(
        {"_id": object_id, "is_deleted": False},
        {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.matched_count > 0


def list_reviews_admin(
    mongo_db: MongoDatabase,
    db: Session,
    *,
    page: int,
    page_size: int,
    product_id: int | None,
    is_deleted: bool | None,
) -> tuple[list[ReviewAdminRead], int]:
    """Danh sách review cho Admin (task mở rộng, KHÔNG có trong
    `docs/API_SPEC.md` bản gốc task 3.2.2/6.x - thêm mới cho trang moderation,
    xem quyết định đã xác nhận). KHÁC `list_product_reviews()`: KHÔNG cứng
    filter `is_deleted: False` - Admin cần thấy CẢ review đã xóa mềm (đúng
    mục đích "audit trail" của thiết kế soft-delete, xem docstring
    `app/schemas/review.py`) - `is_deleted` chỉ lọc khi Admin CHỌN rõ qua
    query param, mặc định (`None`) trả CẢ 2 loại.

    JOIN tên sản phẩm sang MySQL theo BATCH (1 query `WHERE id IN (...)` cho
    toàn bộ `product_id` xuất hiện trong trang hiện tại, KHÔNG phải N+1) -
    cùng convention `order_service.list_orders()` batch-load `order_items`.
    """
    collection = mongo_db[REVIEWS_COLLECTION]
    query_filter: dict = {}
    if product_id is not None:
        query_filter["product_id"] = product_id
    if is_deleted is not None:
        query_filter["is_deleted"] = is_deleted

    total = collection.count_documents(query_filter)
    docs = list(
        collection.find(query_filter).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    )

    product_ids = {doc["product_id"] for doc in docs}
    product_names: dict[int, str] = {}
    if product_ids:
        rows = db.query(Product.id, Product.name).filter(Product.id.in_(product_ids)).all()
        product_names = dict(rows)

    items = [
        ReviewAdminRead.model_validate({**doc, "product_name": product_names.get(doc["product_id"])})
        for doc in docs
    ]
    return items, total
