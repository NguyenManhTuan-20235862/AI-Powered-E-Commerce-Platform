"""Pydantic schema: ProductCatalogSyncEntry (MongoDB collection
`product_catalog_sync`, task 3.5.1).

Xem đầy đủ lý do thiết kế (định nghĩa "hot" tạm thời, tên collection, chọn
`_id`, xử lý sản phẩm bị ẩn) ở docstring `backend/scripts/sync_products_to_mongo.py`
- file này chỉ định nghĩa schema document.

KHÔNG cần `PyObjectId`/`BeforeValidator` kiểu `app/schemas/chat_log.py`/
`review.py` - `_id` ở collection này là `product.id` (MySQL, kiểu `int`)
TRỰC TIẾP, không phải `bson.ObjectId` ngẫu nhiên.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCatalogSyncEntry(BaseModel):
    # alias="_id" - product.id (MySQL) dùng TRỰC TIẾP làm khóa chính Mongo,
    # xem lý do ở docstring sync_products_to_mongo.py mục "Key".
    id: int = Field(alias="_id")
    name: str
    slug: str
    description: str | None = None
    price: Decimal
    # Denormalize tên category (snapshot lúc sync) - cùng đánh đổi đã chọn ở
    # reviews.user_name (task 3.2.2): tránh N+1/join ngược mỗi lần AI Agent
    # đọc, chấp nhận độ lệch nhỏ nếu category đổi tên GIỮA 2 lần sync - độ
    # lệch ở đây còn NHỎ HƠN reviews (job này chạy định kỳ, task 3.5.2, tự
    # làm mới thường xuyên, không phải snapshot vĩnh viễn 1 lần như review).
    category_name: str
    stock_quantity: int
    image_url: str | None = None
    # Thời điểm lần đồng bộ GẦN NHẤT ghi document này - KHÔNG phải thời điểm
    # tạo lần đầu (mỗi lần chạy script, kể cả khi nội dung sản phẩm không đổi
    # gì, field này vẫn cập nhật - dùng để biết dữ liệu "cũ" tới mức nào,
    # hữu ích nếu job lịch (task 3.5.2) có lần chạy bị lỗi/bỏ sót).
    synced_at: datetime

    model_config = ConfigDict(populate_by_name=True)
