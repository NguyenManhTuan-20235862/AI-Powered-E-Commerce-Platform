"""Seed dữ liệu demo: 10 customer, ~70 đơn hàng (order_items tham chiếu 120
sản phẩm demo đã seed ở `scripts/seed_dev_data.py`), review cho các sản phẩm
xuất hiện trong đơn "delivered" - TÁCH RIÊNG khỏi `seed_dev_data.py` (đã xác
nhận với người dùng) vì độ phức tạp khác hẳn: seed category/product là dữ
liệu tĩnh, đây là dữ liệu quan hệ nhiều bảng (MySQL: users/orders/
order_items) + 1 collection MongoDB (reviews).

KHÔNG tự động chain sau `seed_dev_data()` - chạy TAY, SAU KHI đã chạy
`seed_dev_data.py` (script này query thẳng 120 sản phẩm demo theo 6 category
slug cố định, sẽ không có gì để seed nếu chưa chạy `seed_dev_data.py` trước):

    docker compose exec backend python -m scripts.seed_demo_orders_reviews

## Vì sao ghi review TRỰC TIẾP vào MongoDB qua pymongo (không qua API)

`POST /products/{id}/reviews` VẪN `501` (`app/routers/review.py`, review
service layer thuộc task 6.x, xem docs/KNOWN_TODOS.md #12) - API để tạo
review CHƯA TỒN TẠI, không có cách nào khác ngoài insert thẳng document
đúng shape `ReviewInDB` (`app/schemas/review.py`) - đã xác nhận với người
dùng trước khi làm theo hướng này (bypass hoàn toàn validate của 1 endpoint
chưa viết là cách làm bất thường, có chủ đích ở ĐÂY, không phải quy ước
chung cho seed script khác).

## Trừ tồn kho theo trạng thái đơn (đã xác nhận)

Trừ `stock_quantity` cho CẢ `pending`/`confirmed`/`shipping`/`delivered` -
khớp ĐÚNG hành vi thật của `order_service.checkout()` (stock bị trừ NGAY lúc
tạo đơn, không đợi Admin xác nhận) - CHỈ `cancelled` không trừ (tương đương
đã hoàn kho qua `_restock_order_items`). Theo dõi tồn kho "còn lại" bằng 1
dict trong bộ nhớ (`_remaining_stock`) trong suốt quá trình sinh đơn - tránh
sinh order_item vượt quá tồn kho thật của sản phẩm.

## Vì sao "sản phẩm nổi bật" ĐƯỢC GÁN TRỰC TIẾP, KHÔNG chỉ tăng xác suất

Yêu cầu "mỗi sản phẩm nổi bật có 4-5 review" xung đột số học với unique
index MongoDB `(user_id, order_id, product_id)`
(`scripts/create_mongo_indexes.py`) nếu chỉ ĐƠN THUẦN tăng trọng số random
cho 1 nhóm sản phẩm: LẦN THỬ ĐẦU dùng `weighted_pool` (nhân bản sản phẩm
nổi bật trong danh sách rồi `random.choice()`) chỉ đạt tối đa 3 review/sản
phẩm dù đã tăng trọng số x5 cho 25 sản phẩm - vì tổng số order_item
"delivered" thật (~50-55, tính từ ~26-27/~66-70 đơn x 1-3 sản phẩm/đơn) quá
ít so với kỳ vọng thống kê để XÁC SUẤT một mình đảm bảo đủ 4-5 lần/sản
phẩm cho NHIỀU sản phẩm cùng lúc (đã tự kiểm chứng bằng cách chạy thử và
đếm lại qua MongoDB thật - không phải suy đoán lý thuyết).

Cách SỬA: 2 bước tách biệt, GÁN TRỰC TIẾP (chắc chắn, không dựa vào xác
suất) cho phần cần đảm bảo, rồi mới lấp phần còn lại bằng random:
1. Tạo TRƯỚC toàn bộ Order (rỗng, chưa có order_items) cho mọi customer,
   biết chắc đơn nào "delivered".
2. Chỉ chọn `_FEATURED_PRODUCT_COUNT` (12) sản phẩm nổi bật - với số đơn
   delivered thực tế hiện có (~26-27), 12 sản phẩm x mục tiêu 4-5 review =
   48-60 lượt gán, vẫn vừa sức chứa (~26 đơn x tối đa 3 dòng/đơn = tối đa
   78 dòng) - GÁN TRỰC TIẾP từng sản phẩm nổi bật vào ĐỦ số đơn delivered
   RIÊNG BIỆT cần thiết (vòng qua danh sách đơn delivered đã xáo trộn, bỏ
   qua đơn đã đủ 3 dòng hoặc đã có đúng sản phẩm này).
3. Lấp toàn bộ chỗ trống còn lại (mọi đơn, mọi trạng thái) bằng sản phẩm
   ngẫu nhiên (uniform, không cần trọng số nữa - bước 2 đã lo phần cần chắc
   chắn) - vẫn tôn trọng `_remaining_stock`.

Sản phẩm KHÔNG nằm trong nhóm nổi bật vẫn có thể xuất hiện ở bước 3 (kể cả
trong đơn delivered) nhưng KHÔNG được đảm bảo đủ 4-5 - có thể 0-vài review,
đúng thực tế thương mại điện tử (không phải sản phẩm nào cũng có review) -
KHÔNG ép đủ 4-5 cho nhóm này.

## Idempotency (đã xác nhận)

KHÔNG có unique key tự nhiên cho "1 lượt seed order/review của 1 customer".
Cách xử lý: nếu email customer ĐÃ tồn tại VÀ user đó ĐÃ có ít nhất 1 đơn
hàng -> bỏ qua HẲN việc sinh order/review mới cho customer đó (coi như đã
seed xong 1 lần). User CHƯA có đơn (mới tạo, hoặc tồn tại từ trước nhưng
chưa từng seed) vẫn được sinh đơn bình thường.

`random.seed(...)` cố định - kết quả TÁI LẬP ĐƯỢC giữa các lần chạy thật sự
tạo mới (không phải yêu cầu idempotency - đã xử lý riêng ở trên bằng cách
skip theo customer - mà để demo dữ liệu ổn định, dễ đối chiếu khi verify).
"""

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal, get_mongo_db
from app.core.security import hash_password
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole

_DEMO_CATEGORY_SLUGS = ["dien-tu", "thoi-trang", "nha-cua", "lam-dep", "do-choi", "sach"]

_CUSTOMERS = [
    {"full_name": "Nguyễn Văn An", "email": "nguyenvanan@gmail.com", "phone": "0901000001", "address": "12 Đường Lê Lợi, Quận 1, TP.HCM"},
    {"full_name": "Trần Thị Bình", "email": "tranthibinh@gmail.com", "phone": "0901000002", "address": "45 Đường Nguyễn Huệ, Quận 1, TP.HCM"},
    {"full_name": "Lê Hoàng Nam", "email": "lehoangnam@gmail.com", "phone": "0901000003", "address": "78 Đường Trần Hưng Đạo, Quận 5, TP.HCM"},
    {"full_name": "Phạm Thị Hương", "email": "phamthihuong@gmail.com", "phone": "0901000004", "address": "23 Đường Hai Bà Trưng, Quận 3, TP.HCM"},
    {"full_name": "Hoàng Văn Đức", "email": "hoangvanduc@gmail.com", "phone": "0901000005", "address": "56 Đường Cách Mạng Tháng 8, Quận 10, TP.HCM"},
    {"full_name": "Vũ Thị Lan", "email": "vuthilan@gmail.com", "phone": "0901000006", "address": "89 Đường Điện Biên Phủ, Quận Bình Thạnh, TP.HCM"},
    {"full_name": "Đặng Minh Tuấn", "email": "dangminhtuan@gmail.com", "phone": "0901000007", "address": "34 Đường Nguyễn Văn Cừ, Quận 5, TP.HCM"},
    {"full_name": "Bùi Thị Mai", "email": "buithimai@gmail.com", "phone": "0901000008", "address": "67 Đường Lý Thường Kiệt, Quận 11, TP.HCM"},
    {"full_name": "Đỗ Văn Hùng", "email": "dovanhung@gmail.com", "phone": "0901000009", "address": "101 Đường Phan Xích Long, Quận Phú Nhuận, TP.HCM"},
    {"full_name": "Ngô Thị Thu", "email": "ngothithu@gmail.com", "phone": "0901000010", "address": "15 Đường Võ Văn Tần, Quận 3, TP.HCM"},
]
_DEMO_PASSWORD = "Demo@12345"

_FEATURED_PRODUCT_COUNT = 12
_MAX_ITEMS_PER_ORDER = 3

# Tỷ lệ trạng thái đã xác nhận: delivered nhiều nhất ("lịch sử tự nhiên"),
# cancelled ít nhất - biểu diễn bằng 1 danh sách 20 phần tử để random.choice
# xấp xỉ đúng tỷ lệ % mà không cần thư viện thống kê riêng.
_STATUS_POOL = (
    [OrderStatus.delivered] * 8
    + [OrderStatus.confirmed] * 4
    + [OrderStatus.shipping] * 3
    + [OrderStatus.pending] * 3
    + [OrderStatus.cancelled] * 2
)

_RATING_POOL = [5] * 40 + [4] * 35 + [3] * 15 + [2] * 7 + [1] * 3

_COMMENT_TEMPLATES: dict[int, list[str]] = {
    5: [
        "Sản phẩm rất tốt, đúng như mô tả, sẽ ủng hộ shop tiếp!",
        "Chất lượng vượt mong đợi, giao hàng nhanh, đóng gói cẩn thận.",
        "Dùng rất ưng ý, giá hợp lý so với chất lượng.",
        "Tuyệt vời, đúng nhu cầu, sẽ giới thiệu cho bạn bè.",
    ],
    4: [
        "Sản phẩm ổn, dùng tốt, giao hàng hơi chậm một chút.",
        "Chất lượng khá tốt, đóng gói cẩn thận, sẽ mua lại.",
        "Hài lòng với sản phẩm, giá cả hợp lý.",
        "Nhìn chung ổn, phù hợp với mô tả trên trang.",
    ],
    3: [
        "Sản phẩm tạm ổn, không có gì đặc biệt.",
        "Dùng được nhưng chưa thật sự ấn tượng.",
        "Chất lượng ở mức trung bình so với giá tiền.",
    ],
    2: [
        "Sản phẩm không như mong đợi, chất lượng chưa tốt.",
        "Hơi thất vọng, giao hàng cũng chậm.",
    ],
    1: [
        "Không hài lòng, sản phẩm khác nhiều so với mô tả.",
    ],
}


def _get_or_create_customer(db, data: dict) -> tuple[User, bool]:
    """Trả về (user, has_existing_orders) - `has_existing_orders=True` nghĩa
    là customer này ĐÃ được seed order/review từ lần chạy trước, phải bỏ qua
    (xem quyết định idempotency ở docstring module)."""
    user = db.query(User).filter(User.email == data["email"]).one_or_none()
    if user is None:
        user = User(
            email=data["email"],
            password_hash=hash_password(_DEMO_PASSWORD),
            full_name=data["full_name"],
            phone=data["phone"],
            address=data["address"],
            role=UserRole.customer,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user, False

    has_orders = db.query(Order.id).filter(Order.user_id == user.id).first() is not None
    return user, has_orders


def _load_demo_products(db) -> list[Product]:
    category_ids = [c.id for c in db.query(Category).filter(Category.slug.in_(_DEMO_CATEGORY_SLUGS)).all()]
    return db.query(Product).filter(Product.category_id.in_(category_ids)).all()


class _OrderPlan:
    """1 đơn hàng đang được xây dựng trong bộ nhớ - CHƯA insert OrderItem,
    chỉ giữ danh sách (product, quantity) tạm - `total_amount` tính 1 lần
    cuối cùng sau khi đã chốt đủ item (kể cả phần "nổi bật" lẫn phần lấp chỗ
    trống ngẫu nhiên)."""

    def __init__(self, order: Order, target_item_count: int):
        self.order = order
        self.target_item_count = target_item_count
        self.items: list[tuple[Product, int]] = []
        self.product_ids: set[int] = set()

    def has_room(self) -> bool:
        return len(self.items) < self.target_item_count

    def add(self, product: Product, quantity: int) -> None:
        self.items.append((product, quantity))
        self.product_ids.add(product.id)


def _create_empty_orders(db, customers_to_seed: list[User]) -> list[_OrderPlan]:
    """Tạo TRƯỚC toàn bộ Order (status/created_at/shipping_* đã chốt, CHƯA có
    order_items) cho mọi customer cần seed - biết chắc đơn nào "delivered"
    TRƯỚC KHI phân bổ sản phẩm, phục vụ bước gán "sản phẩm nổi bật" ở
    `_assign_featured_products()`."""
    now = datetime.now()  # naive - khớp convention Order.created_at (DateTime không timezone)
    plans: list[_OrderPlan] = []

    for user in customers_to_seed:
        num_orders = random.randint(6, 8)
        for _ in range(num_orders):
            status = random.choice(_STATUS_POOL)
            created_at = now - timedelta(days=random.randint(0, 75), hours=random.randint(0, 23))
            order = Order(
                user_id=user.id,
                status=status,
                total_amount=Decimal("0"),
                shipping_name=user.full_name,
                shipping_address=user.address,
                shipping_phone=user.phone,
                created_at=created_at,
            )
            db.add(order)
            db.flush()  # cần order.id ngay để gán featured products theo đúng đơn
            plans.append(_OrderPlan(order, random.randint(1, _MAX_ITEMS_PER_ORDER)))

    return plans


def _assign_featured_products(
    plans: list[_OrderPlan], demo_products: list[Product], remaining_stock: dict[int, int]
) -> list[Product]:
    """GÁN TRỰC TIẾP (không dựa vào xác suất) `_FEATURED_PRODUCT_COUNT` sản
    phẩm vào đủ 4-5 đơn "delivered" RIÊNG BIỆT mỗi sản phẩm - xem giải thích
    đầy đủ ở docstring module. Trả về danh sách sản phẩm nổi bật đã chọn."""
    featured = random.sample(demo_products, _FEATURED_PRODUCT_COUNT)

    delivered_plans = [p for p in plans if p.order.status == OrderStatus.delivered]
    random.shuffle(delivered_plans)

    for product in featured:
        target = random.randint(4, 5)
        assigned = 0
        for plan in delivered_plans:
            if assigned >= target:
                break
            if not plan.has_room() or product.id in plan.product_ids:
                continue
            qty = min(random.randint(1, 3), remaining_stock[product.id])
            if qty <= 0:
                continue
            plan.add(product, qty)
            remaining_stock[product.id] -= qty
            assigned += 1
        if assigned < target:
            print(f"    (lưu ý: sản phẩm nổi bật '{product.name}' chỉ gán được {assigned}/{target} đơn delivered - hết chỗ trống/hết tồn kho)")

    return featured


def _fill_remaining_items(plans: list[_OrderPlan], demo_products: list[Product], remaining_stock: dict[int, int]) -> None:
    """Lấp toàn bộ chỗ trống còn lại (mọi đơn, mọi trạng thái) bằng sản phẩm
    ngẫu nhiên ĐỀU (uniform) - bước `_assign_featured_products()` đã lo phần
    cần đảm bảo chắc chắn, bước này không cần trọng số nữa. `cancelled` không
    kiểm tra/trừ `remaining_stock` (đơn hủy không thật sự tiêu tốn tồn kho)."""
    for plan in plans:
        attempts = 0
        while plan.has_room() and attempts < 30:
            attempts += 1
            product = random.choice(demo_products)
            if product.id in plan.product_ids:
                continue
            qty = random.randint(1, 3)
            if plan.order.status != OrderStatus.cancelled:
                available = remaining_stock[product.id]
                if available <= 0:
                    continue
                qty = min(qty, available)
                remaining_stock[product.id] -= qty
            plan.add(product, qty)


def _finalize_orders(db, plans: list[_OrderPlan]) -> None:
    """Ghi `order_items` thật + tính `total_amount` cuối cùng cho MỌI đơn -
    gọi SAU KHI cả 2 bước gán sản phẩm (nổi bật + lấp chỗ trống) đã xong."""
    for plan in plans:
        total = Decimal("0")
        for product, qty in plan.items:
            total += product.price * qty
            db.add(
                OrderItem(
                    order_id=plan.order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=qty,
                    price_at_purchase=product.price,
                )
            )
        plan.order.total_amount = total


def _seed_orders(db, demo_products: list[Product]) -> list[Order]:
    """Trả về danh sách Order MỚI vừa tạo (dùng để seed review ngay sau,
    KHÔNG cần query lại) - bỏ qua hoàn toàn customer đã có đơn từ trước."""
    remaining_stock: dict[int, int] = {p.id: p.stock_quantity for p in demo_products}

    customers_to_seed: list[User] = []
    for customer_data in _CUSTOMERS:
        user, has_orders = _get_or_create_customer(db, customer_data)
        if has_orders:
            print(f"  = {customer_data['email']} đã có đơn hàng từ trước, bỏ qua seed order/review")
            continue
        customers_to_seed.append(user)

    if not customers_to_seed:
        return []

    plans = _create_empty_orders(db, customers_to_seed)
    print(f"  + tạo {len(plans)} đơn hàng (rỗng) cho {len(customers_to_seed)} customer mới")

    featured = _assign_featured_products(plans, demo_products, remaining_stock)
    print(f"  + đã gán {len(featured)} sản phẩm nổi bật vào đủ đơn delivered (xem log nếu có sản phẩm không đủ chỗ)")

    _fill_remaining_items(plans, demo_products, remaining_stock)
    _finalize_orders(db, plans)

    for product in demo_products:
        product.stock_quantity = remaining_stock[product.id]

    return [plan.order for plan in plans]


def _seed_reviews(db, new_orders: list[Order]) -> None:
    """Chỉ xét đơn `delivered` trong `new_orders` (đơn MỚI vừa tạo trong lần
    chạy này) - review theo unique index (user_id, order_id, product_id),
    mỗi sản phẩm nhận tối đa 4-5 review NHƯNG KHÔNG VƯỢT QUÁ số đơn delivered
    khác nhau THẬT SỰ có sản phẩm đó."""
    if not new_orders:
        print("  Không có đơn hàng mới - bỏ qua seed review.")
        return

    delivered_order_ids = {o.id: o for o in new_orders if o.status == OrderStatus.delivered}
    if not delivered_order_ids:
        print("  Không có đơn 'delivered' nào trong lần chạy này - bỏ qua seed review.")
        return

    users_by_id = {u.id: u for u in db.query(User).filter(User.id.in_({o.user_id for o in new_orders})).all()}

    order_items = db.query(OrderItem).filter(OrderItem.order_id.in_(delivered_order_ids.keys())).all()
    # product_id -> list (user_id, user_name, order_id) - MỖI đơn delivered
    # đóng góp ĐÚNG 1 cặp hợp lệ / sản phẩm (khớp unique index chỉ cho 1
    # review/(user, order, product)).
    candidates_by_product: dict[int, list[tuple[int, str, int]]] = {}
    seen_pairs: set[tuple[int, int]] = set()
    for item in order_items:
        pair = (item.order_id, item.product_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        order = delivered_order_ids[item.order_id]
        user = users_by_id[order.user_id]
        candidates_by_product.setdefault(item.product_id, []).append((user.id, user.full_name, order.id))

    reviews_collection = get_mongo_db()["reviews"]
    now = datetime.now(timezone.utc)
    total_reviews = 0

    for product_id, candidates in candidates_by_product.items():
        random.shuffle(candidates)
        target = random.randint(4, 5)
        selected = candidates[: min(target, len(candidates))]

        for user_id, user_name, order_id in selected:
            order = delivered_order_ids[order_id]
            rating = random.choice(_RATING_POOL)
            comment = random.choice(_COMMENT_TEMPLATES[rating])
            review_created_at = order.created_at.replace(tzinfo=timezone.utc) + timedelta(days=random.randint(3, 14))
            if review_created_at > now:
                review_created_at = now

            reviews_collection.insert_one(
                {
                    "product_id": product_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "order_id": order_id,
                    "rating": rating,
                    "comment": comment,
                    "images": None,
                    "is_verified_purchase": True,
                    "is_deleted": False,
                    "created_at": review_created_at,
                    "updated_at": None,
                }
            )
            total_reviews += 1

    print(f"  + {total_reviews} review mới được tạo cho {len(candidates_by_product)} sản phẩm delivered")


def seed_demo_orders_reviews() -> None:
    random.seed(20260830)

    db = SessionLocal()
    try:
        demo_products = _load_demo_products(db)
        if len(demo_products) < _FEATURED_PRODUCT_COUNT:
            raise RuntimeError(
                "Chưa đủ sản phẩm demo - chạy `python -m scripts.seed_dev_data` trước khi chạy script này."
            )

        print("Order (10 customer, ~70 đơn):")
        new_orders = _seed_orders(db, demo_products)
        db.commit()

        print("Review (MongoDB, chỉ đơn delivered):")
        _seed_reviews(db, new_orders)
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_orders_reviews()
