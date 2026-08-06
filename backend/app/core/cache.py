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


def invalidate_by_prefix(redis_client: redis.Redis, prefix: str) -> None:
    """Xóa TOÀN BỘ key Redis có tiền tố `prefix` (task 3.4.1 - invalidate chủ
    động cache danh sách sản phẩm sau CRUD, thay cho chỉ dựa vào TTL như
    quyết định ban đầu ở task 3.3.1 - đổi quyết định sau khi xác nhận lại với
    người dùng: giờ đã có API CRUD thật, độ trễ tới 5 phút lộ rõ và khó chịu
    hơn hẳn lúc còn là phân tích trừu tượng).

    Dùng cho MỌI domain cache theo pattern "1 filter/tham số sinh ra nhiều
    biến thể key" (không chỉ sản phẩm) - gọi với đúng tiền tố dùng chung của
    domain đó (VD `products:list:`, sau này có thể là `categories:list:`).

    Dùng SCAN (`scan_iter`) thay vì lệnh KEYS - KEYS chặn (block) toàn bộ
    Redis tới khi quét xong toàn bộ keyspace, nguy hiểm nếu keyspace lớn ở
    production thật; SCAN duyệt theo cursor, không chặn. Ở quy mô đồ án (vài
    trăm key) khác biệt hiệu năng không đáng kể, nhưng chọn cách đúng
    nguyên tắc ngay từ đầu không tốn thêm gì.

    Redis lỗi (mất kết nối...) - CHỈ log warning, KHÔNG raise: invalidate
    thất bại nghĩa là cache CŨ có thể còn thêm 1 lúc (vẫn có trần giới hạn -
    TTL của key đó), không phải lỗi nghiêm trọng cần chặn request CRUD đang
    xử lý (dữ liệu nguồn - MySQL/MongoDB - đã ghi đúng, chỉ cache hiển thị có
    thể trễ thêm chút ít, giống triết lý fail-soft của `get_or_set_cache`).
    """
    try:
        keys = list(redis_client.scan_iter(match=f"{prefix}*"))
        if keys:
            redis_client.delete(*keys)
    except redis.RedisError:
        logger.warning(
            "Redis lỗi lúc invalidate cache (prefix=%s) - bỏ qua, cache cũ có thể còn tới hết TTL",
            prefix,
            exc_info=True,
        )
