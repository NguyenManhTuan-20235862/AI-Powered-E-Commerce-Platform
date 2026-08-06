"""Đồng bộ 1 CHIỀU Product (MySQL) -> collection MongoDB `product_catalog_sync`
(task 3.5.1) - phục vụ AI Agent (task 6.x) truy vấn nhanh lúc tư vấn/RAG mà
không cần query trực tiếp MySQL mỗi lần.

## "Sản phẩm hot" - ĐỊNH NGHĨA TẠM THỜI, sẽ cần cập nhật

Task gọi đây là đồng bộ sản phẩm "hot" (bán chạy/phổ biến) nhưng CHƯA CÓ dữ
liệu đủ để xếp hạng theo nghĩa đó thật sự - dashboard thống kê (task 5.3) và
AI Agent thật (task 6.x) đều chưa tồn tại để cung cấp tín hiệu doanh số/lượt
xem đáng tin cậy (dù bảng `orders`/`order_items` đã có dữ liệu thật từ task
3.4.2, CHƯA có logic tổng hợp "bán chạy" nào dùng nó).

ĐỊNH NGHĨA TẠM THỜI ở giai đoạn này: đồng bộ TOÀN BỘ sản phẩm `is_active=True`
(KHÔNG lọc/xếp hạng theo "hot" thật). Lý do: mục đích cuối của collection này
là phục vụ AI Agent RAG trả lời được VỀ BẤT KỲ sản phẩm nào đang bán, không
chỉ top-N sản phẩm bán chạy nhất - giới hạn sớm ở bước đồng bộ sẽ khiến AI
Agent "mù" với phần lớn catalog dù khách hỏi đúng sản phẩm đó.

KHI task 6.x có dữ liệu order thật đủ lớn để tính "bán chạy" (VD
`SUM(order_items.quantity) GROUP BY product_id` trong khung thời gian nào
đó): cân nhắc THÊM 1 field điểm phổ biến/ranking vào MỖI document (KHÔNG đổi
PHẠM VI đồng bộ - vẫn toàn bộ active) để AI Agent tự sắp xếp/ưu tiên lúc
truy vấn, thay vì đổi lại tập hợp sản phẩm được đồng bộ.

## Tên collection: `product_catalog_sync`

KHÔNG trùng/nhầm với `chat_logs` (task 3.2.1)/`reviews` (task 3.2.2) đã có -
tên phản ánh đúng bản chất: bản sao (snapshot đồng bộ định kỳ) của catalog
sản phẩm, không phải dữ liệu gốc (MySQL `products` vẫn là nguồn sự thật).

## Key: `_id` = `product.id` (MySQL) TRỰC TIẾP

KHÔNG dùng ObjectId ngẫu nhiên + field riêng để đối chiếu ngược - MongoDB
cho phép `_id` là bất kỳ kiểu nào (không bắt buộc ObjectId). Dùng thẳng
`product.id` (int) làm `_id`:
- Upsert đơn giản (`replace_one({"_id": product.id}, ...)` - 1 điều kiện
  duy nhất, tận dụng index `_id` mặc định, không cần index phụ).
- Đối chiếu ngược với MySQL tức thời, không cần field `mysql_product_id`
  riêng trùng lặp thông tin đã nằm sẵn trong `_id`.

## Xử lý sản phẩm bị ẩn (`is_active=False`) sau lần sync trước

XÓA CỨNG document tương ứng khỏi Mongo - KHÔNG soft-delete kiểu `reviews`
(`is_deleted` flag, task 3.2.2). Quyết định có chủ đích, khác hẳn lý do ở
`reviews`:
- `reviews.is_deleted` tồn tại vì lý do MODERATION/AUDIT TRAIL (biết Admin
  xóa review nào, có thể tranh chấp sau này) - `product_catalog_sync` KHÔNG
  có nhu cầu đó, đây chỉ là BẢN SAO DẪN XUẤT (derived) của MySQL; nguồn sự
  thật (`products.is_active`, đã có soft-delete + lịch sử riêng) vẫn nằm ở
  MySQL, không mất gì khi xóa cứng bản sao ở Mongo.
- Xóa cứng đảm bảo AI Agent RAG (task 6.x) - DÙ code truy vấn có lỡ quên
  filter `is_active` hay không - KHÔNG THỂ gợi ý nhầm sản phẩm đã ẩn/ngừng
  bán (document không tồn tại thì không truy vấn ra được, đây là yêu cầu
  "không được xảy ra" - mạnh hơn hẳn cơ chế "nhớ phải filter đúng" mà
  soft-delete + query filter yêu cầu ở mọi nơi đọc dữ liệu).
- Sản phẩm active lại sau này (Admin bật lại `is_active=True`) tự động được
  đồng bộ lại ở lần chạy script kế tiếp - collection này luôn tái tạo được
  HOÀN TOÀN từ MySQL, không có rủi ro mất dữ liệu vĩnh viễn khi xóa cứng ở
  đây (khác hẳn xóa cứng 1 bảng nguồn sự thật thật sự).

## Idempotent

`replace_one(..., upsert=True)` theo `_id` - chạy lại nhiều lần liên tiếp
cho CÙNG dữ liệu MySQL luôn cho ra CÙNG 1 document (không tạo trùng, không
lỗi). `synced_at` đổi mỗi lần chạy - đây là hành vi ĐÚNG mong muốn (dấu thời
gian đồng bộ phải cập nhật), không phải vi phạm idempotent (nội dung sản
phẩm không đổi thì phần còn lại của document giữ nguyên).

## Vì sao là script riêng (backend/scripts/), KHÔNG chạy trong tiến trình FastAPI

Cùng lý do đã áp dụng cho `create_mongo_indexes.py` (task 3.2.3): đây là
thao tác BATCH/định kỳ (task 3.5.2 sẽ lên lịch chạy - APScheduler hoặc cơ
chế khác), khác hẳn vòng đời request/response của router - KHÔNG import/gọi
từ `app/main.py`, KHÔNG tự chạy khi có request HTTP nào. Giữ ở dạng hàm callable
độc lập (`sync_products_to_mongo()`) để task 3.5.2 vẫn linh hoạt CHỌN cơ chế
lịch chạy sau (APScheduler nhúng trong tiến trình FastAPI, hay cron/container
riêng ngoài web server) mà không phải viết lại logic đồng bộ - chỉ cần
import + gọi hàm này từ bất kỳ đâu.

## Cách chạy (giống `scripts/seed_admin.py`/`scripts/create_mongo_indexes.py`)

Trong container backend dev:
    docker compose exec backend python -m scripts.sync_products_to_mongo
"""

import logging
from datetime import datetime, timezone

from bson import Decimal128

from app.core.database import SessionLocal, get_mongo_db
from app.core.logging import setup_logging
from app.models.category import Category
from app.models.product import Product
from app.schemas.product_catalog_sync import ProductCatalogSyncEntry

logger = logging.getLogger(__name__)

COLLECTION_NAME = "product_catalog_sync"


def sync_products_to_mongo() -> None:
    db = SessionLocal()
    try:
        # JOIN thẳng categories (KHÔNG dùng relationship(), cùng convention
        # đã dùng ở app/services/product_service.py) - 1 query duy nhất lấy
        # đủ tên category cho toàn bộ sản phẩm, tránh N+1.
        rows = (
            db.query(Product, Category.name)
            .join(Category, Product.category_id == Category.id)
            .filter(Product.is_active.is_(True))
            .all()
        )
    finally:
        db.close()

    collection = get_mongo_db()[COLLECTION_NAME]

    synced_at = datetime.now(timezone.utc)
    active_ids: set[int] = set()
    new_count = 0
    updated_count = 0

    for product, category_name in rows:
        entry = ProductCatalogSyncEntry(
            id=product.id,
            name=product.name,
            slug=product.slug,
            description=product.description,
            price=product.price,
            category_name=category_name,
            stock_quantity=product.stock_quantity,
            image_url=product.image_url,
            synced_at=synced_at,
        )
        # BSON (định dạng wire của MongoDB) KHÔNG tự encode được
        # decimal.Decimal (PyMongo raise InvalidDocument nếu truyền thẳng,
        # đã tự kiểm chứng) - chuyển sang bson.Decimal128, kiểu số THẬP PHÂN
        # CHÍNH XÁC đúng chuẩn BSON cho tiền tệ (KHÔNG dùng float - mất chính
        # xác, không phù hợp cho giá tiền). Chuyển qua str(Decimal) trước khi
        # đưa vào Decimal128 - tránh sai số nhị phân nếu đi qua float trung gian.
        doc = entry.model_dump(by_alias=True)
        doc["price"] = Decimal128(str(entry.price))
        result = collection.replace_one(
            {"_id": entry.id},
            doc,
            upsert=True,
        )
        active_ids.add(entry.id)
        if result.upserted_id is not None:
            new_count += 1
        else:
            updated_count += 1

    # Sản phẩm ĐÃ TỪNG sync (còn document trong Mongo) nhưng giờ KHÔNG còn
    # trong tập active_ids (đã is_active=False, hoặc hiếm hơn - đã bị xóa
    # khỏi MySQL) - xóa cứng, xem lý do đầy đủ ở docstring module.
    existing_ids = {doc["_id"] for doc in collection.find({}, {"_id": 1})}
    stale_ids = existing_ids - active_ids
    removed_count = 0
    if stale_ids:
        removed_count = collection.delete_many({"_id": {"$in": list(stale_ids)}}).deleted_count

    logger.info(
        "Đồng bộ %s xong: %d sản phẩm active (%d mới, %d cập nhật), %d đã ẩn/gỡ khỏi Mongo",
        COLLECTION_NAME,
        len(active_ids),
        new_count,
        updated_count,
        removed_count,
    )


if __name__ == "__main__":
    setup_logging()
    sync_products_to_mongo()
