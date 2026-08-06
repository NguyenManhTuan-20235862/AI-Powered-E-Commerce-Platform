"""Verify `get_or_set_cache()` (task 3.3.1) TRỰC TIẾP qua 1 hàm query Product
demo - KHÔNG qua router/API (`GET /products` thật CHƯA tồn tại, vẫn `501` -
đó là task 3.4.1). Khi task 3.4.1 implement `GET /products` thật, chỉ cần
gọi lại `get_or_set_cache()` (`app/core/cache.py`) với `fetch_fn` là hàm query
Product THẬT (thay cho `_fetch_hot_products_demo` chỉ tồn tại trong file test
này) - không viết lại logic cache.

TTL đề xuất cho danh sách sản phẩm hot khi lên thật: 300-600s (5-10 phút) -
xem lý do ở hằng số `RECOMMENDED_HOT_PRODUCTS_TTL_SECONDS` bên dưới. Test này
tự dùng TTL ngắn hơn nhiều (2s) chỉ để verify hết hạn nhanh, KHÔNG phải giá
trị đề xuất dùng thật.
"""

import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, TypeAdapter
from sqlalchemy.orm import Session

from app.core.cache import get_or_set_cache
from app.models.category import Category
from app.models.product import Product

# 5-10 phút: cân bằng giữa "dữ liệu đủ mới" và "giảm tải MySQL thật sự đáng
# kể". Danh sách sản phẩm hot không cần chính xác tới từng giây (khác
# stock_quantity - luôn đọc thật lúc checkout, task 8.2 SELECT FOR UPDATE,
# KHÔNG qua cache) - 5-10 phút lệch là chấp nhận được cho mục đích hiển thị.
# Ngắn hơn (VD 30s) gần như không giảm tải được gì nếu traffic đọc dồn dập
# (mỗi 30s lại query DB 1 lần cho MỌI request trong nhiều giờ cao điểm); dài
# hơn (VD 1h) khiến sản phẩm mới/đổi giá không kịp lên danh sách hot trong
# thời gian dài, trải nghiệm admin "sao vừa sửa mà chưa thấy đổi" khó chịu.
RECOMMENDED_HOT_PRODUCTS_TTL_SECONDS = 300


class _HotProductDemo(BaseModel):
    """Schema DEMO riêng cho test này - CỐ TÌNH KHÔNG dùng
    `app/schemas/product.py` (`ProductRead`): schema đó vẫn là placeholder cũ
    từ trước khi model `Product` thật tồn tại (task 3.1.2) - lệch hẳn so với
    model thật (`id`/`category_id` khai `str` thay vì `int`, thiếu
    `is_active`/`slug`/`created_at`, field tên `stock` thay vì đúng tên cột
    `stock_quantity`). KHÔNG sửa `ProductRead` ở task 3.3.1 - ngoài phạm vi
    (task 3.4.1 tự thiết kế lại schema Product đầy đủ khi implement CRUD
    thật) - đã báo lại phát hiện này cho người dùng, xem thêm
    `docs/KNOWN_TODOS.md`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal


def _fetch_hot_products_demo(db: Session) -> list[_HotProductDemo]:
    """Hàm query DEMO - CHỈ để verify cơ chế cache (hit/miss/TTL) hoạt động
    đúng, KHÔNG PHẢI logic "phổ biến" thật (xếp hạng theo lượt bán từ
    order_items là quyết định nghiệp vụ của task 3.4.1/sau này, ngoài phạm vi
    task 3.3.1 - task này chỉ cần 1 nguồn dữ liệu MySQL thật bất kỳ để verify
    cache, không cần đúng thuật toán "phổ biến").

    `time.sleep(0.05)` giả lập query chậm - CHỈ tồn tại trong test này để
    phép so sánh thời gian hit/miss ổn định, không bị nhiễu bởi việc query
    thật trên MySQL gần như rỗng vốn đã rất nhanh (vài ms, chênh lệch với
    Redis GET có thể không đáng tin cậy để assert). KHÔNG xuất hiện trong
    code thật (task 3.4.1 sẽ không có dòng sleep này).
    """
    time.sleep(0.05)
    products = db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.id).all()
    return [_HotProductDemo.model_validate(p) for p in products]


def _seed_products(db: Session) -> None:
    category = Category(name="Demo Cache", slug="demo-cache-test")
    db.add(category)
    db.flush()
    db.add_all(
        [
            Product(
                category_id=category.id,
                name="Sản phẩm A",
                slug="sp-a-cache-test",
                price=Decimal("100000.00"),
                stock_quantity=10,
                is_active=True,
            ),
            Product(
                category_id=category.id,
                name="Sản phẩm B",
                slug="sp-b-cache-test",
                price=Decimal("200000.00"),
                stock_quantity=5,
                is_active=True,
            ),
        ]
    )
    db.commit()


def test_cache_hit_faster_than_miss_and_returns_correct_data(db: Session, redis_client) -> None:
    _seed_products(db)
    adapter = TypeAdapter(list[_HotProductDemo])
    key = "test:products:hot:page:1"

    start_miss = time.perf_counter()
    result_miss = get_or_set_cache(redis_client, key, lambda: _fetch_hot_products_demo(db), ttl_seconds=60, adapter=adapter)
    duration_miss = time.perf_counter() - start_miss

    start_hit = time.perf_counter()
    result_hit = get_or_set_cache(redis_client, key, lambda: _fetch_hot_products_demo(db), ttl_seconds=60, adapter=adapter)
    duration_hit = time.perf_counter() - start_hit

    assert len(result_miss) == 2
    assert {p.name for p in result_miss} == {"Sản phẩm A", "Sản phẩm B"}
    assert result_hit == result_miss

    # Miss có sleep 0.05s giả lập - hit (chỉ đọc Redis) phải nhanh hơn HẲN,
    # không chỉ nhỉnh hơn 1 chút (dễ nhiễu) - assert ngưỡng tuyệt đối rõ ràng
    # thay vì chỉ so sánh hit < miss.
    assert duration_hit < 0.02
    assert duration_miss >= 0.05


def test_cache_ttl_expires(db: Session, redis_client) -> None:
    _seed_products(db)
    adapter = TypeAdapter(list[_HotProductDemo])
    key = "test:products:hot:ttl-check"

    get_or_set_cache(redis_client, key, lambda: _fetch_hot_products_demo(db), ttl_seconds=2, adapter=adapter)
    assert redis_client.get(key) is not None

    time.sleep(2.5)
    assert redis_client.get(key) is None
