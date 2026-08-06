"""Cache utility dùng chung qua Redis (task 3.3.1).

`get_or_set_cache()` - pattern cache-aside chuẩn: check cache (Redis) trước,
nếu miss thì gọi `fetch_fn()` lấy dữ liệu THẬT (MySQL/MongoDB...), lưu vào
cache với TTL rồi trả về. Serialize/deserialize qua JSON bằng
`pydantic.TypeAdapter` - hoạt động với BẤT KỲ type nào Pydantic hỗ trợ, kể cả
`list[SomeModel]` (không chỉ 1 model đơn lẻ) - không cần viết logic serialize
riêng cho từng trường hợp dùng cache.

TÁI SỬ DỤNG: hàm này KHÔNG có gì đặc thù riêng cho "sản phẩm phổ biến" (task
3.3.1, xem ví dụ dùng thật ở `tests/test_cache.py`) - dùng được cho MỌI nhu
cầu cache khác sau này (category list, dashboard stats task 5.3...), miễn
truyền đúng `key`/`fetch_fn`/`ttl_seconds`/`adapter` tương ứng. Khi task 3.4.1
implement `GET /products` thật, chỉ cần gọi lại đúng hàm này (xem hướng dẫn ở
`docs/DATABASE_SCHEMA.md`/comment trong `tests/test_cache.py`), KHÔNG viết
lại logic cache.

Redis lỗi (mất kết nối, timeout...) KHÔNG làm request thất bại - cache là lớp
TỐI ƯU, không phải nguồn dữ liệu chính thức: coi như cache miss, fallback gọi
thẳng `fetch_fn()` (chậm hơn nhưng vẫn đúng), chỉ log warning. Nguồn dữ liệu
thật (`fetch_fn`, đọc MySQL/MongoDB) mới là nơi lỗi thật sự cần raise ra
ngoài - không nuốt lỗi ở đó.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

import redis
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_or_set_cache(
    redis_client: redis.Redis,
    key: str,
    fetch_fn: Callable[[], T],
    ttl_seconds: int,
    adapter: TypeAdapter[T],
) -> T:
    """Trả về dữ liệu từ cache (Redis) nếu có, ngược lại gọi `fetch_fn()` lấy
    dữ liệu thật rồi lưu vào cache với TTL `ttl_seconds` giây.

    - `key`: cache key - quy ước đặt tên `<domain>:<mô_tả>[:<tham_số>...]`
      (VD `products:hot:page:1`) - phân cấp bằng dấu `:` để dễ mở rộng thêm
      filter/phân trang sau này (VD `products:hot:category:5:page:2`) mà
      không đụng tới key cũ.
    - `fetch_fn`: hàm KHÔNG NHẬN THAM SỐ, trả về đúng type mà `adapter` mô tả
      (VD `lambda: get_hot_products(db)`) - CHỈ gọi khi cache miss.
    - `adapter`: `pydantic.TypeAdapter` ứng với type trả về của `fetch_fn`
      (VD `TypeAdapter(list[ProductRead])`) - truyền TƯỜNG MINH thay vì tự
      suy luận type từ `fetch_fn` lúc runtime (introspection kiểu đó không
      đáng tin cậy với lambda/closure) - caller luôn biết rõ đang cache type
      gì, không có gì "ma thuật" ở hàm này.
    """
    try:
        cached = redis_client.get(key)
    except redis.RedisError:
        logger.warning("Redis GET lỗi (key=%s) - fallback gọi fetch_fn() trực tiếp", key, exc_info=True)
        cached = None

    if cached is not None:
        return adapter.validate_json(cached)

    value = fetch_fn()

    try:
        redis_client.set(key, adapter.dump_json(value).decode("utf-8"), ex=ttl_seconds)
    except redis.RedisError:
        logger.warning(
            "Redis SET lỗi (key=%s) - bỏ qua, dữ liệu vẫn trả về đúng, chỉ không cache được lần này",
            key,
            exc_info=True,
        )

    return value
