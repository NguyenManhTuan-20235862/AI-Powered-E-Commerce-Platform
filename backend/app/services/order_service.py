"""Business logic: Order (task 3.4.2) - tách khỏi router app/routers/order.py.

`checkout()` là nơi ĐẦU TIÊN trong dự án dùng `SELECT ... FOR UPDATE` thật
(task 8.2 trong WBS thực chất nằm trong phạm vi task này, không phải task
riêng biệt về sau - xem CLAUDE.md/docs/KNOWN_TODOS.md #1 đã note trước).

## Vì sao phải khóa TỪNG sản phẩm trong giỏ, không chỉ 1 dòng

1 đơn hàng có thể gồm NHIỀU sản phẩm khác nhau (nhiều dòng `cart_items`, mỗi
dòng 1 `product_id`) - THIẾU tồn kho ở BẤT KỲ sản phẩm nào trong số đó cũng
phải chặn TOÀN BỘ đơn hàng (không đặt hàng "một nửa" - VD giỏ có Áo + Quần,
Áo hết hàng thì không được tạo đơn chỉ có Quần, khách không đặt vậy). Vì vậy
phải khóa (`SELECT ... FOR UPDATE`) ĐỦ MỌI sản phẩm liên quan TRƯỚC khi quyết
định tạo đơn, không phải chỉ dòng đầu tiên.

## Vì sao khóa theo thứ tự `product_id` TĂNG DẦN (tránh deadlock)

2 user đặt hàng ĐỒNG THỜI, cùng có 2 sản phẩm A (id=3) và B (id=5) trong giỏ
nhưng thêm vào giỏ theo thứ tự KHÁC NHAU (user 1: B rồi A; user 2: A rồi B).
Nếu khóa theo đúng thứ tự trong giỏ hàng (không sắp xếp lại), user 1 khóa B
trước rồi chờ khóa A - CÙNG LÚC user 2 khóa A trước rồi chờ khóa B -> DEADLOCK
thật (2 transaction chờ nhau vô thời hạn, MySQL/InnoDB tự phát hiện và hủy 1
trong 2 với lỗi "Deadlock found when trying to get lock"). Khóa LUÔN theo thứ
tự `product_id` TĂNG DẦN (bất kể thứ tự thêm vào giỏ) khiến MỌI transaction
đều khóa theo ĐÚNG 1 thứ tự toàn cục duy nhất - về mặt cấu trúc KHÔNG THỂ xảy
ra chờ vòng tròn (circular wait) nữa, deadlock giữa 2 giao dịch checkout
không còn khả năng xảy ra (không phải "ít xảy ra hơn" - loại bỏ HẲN).

## Vì sao khóa CẢ `cart_items` của chính user đó (không chỉ `products`)

Bảo vệ luôn trường hợp user tự double-submit (bấm đúp nút "Đặt hàng", hoặc
request bị retry do mạng chập chờn) - 2 request checkout gần như đồng thời
từ CÙNG 1 user. Khóa `cart_items` của user này TRƯỚC khi đọc khiến request
THỨ HAI phải CHỜ request đầu commit (xóa cart_items) xong mới đọc được -
lúc đó giỏ hàng đã trống, request thứ hai tự nhiên nhận lỗi "giỏ hàng trống"
thay vì tạo đơn trùng. Không tốn thêm hạ tầng gì (không cần Redis lock riêng)
vì `cart_items` vốn đã cần đọc trong transaction này, cùng cơ chế khóa với
`products` - chỉ khác đối tượng bị khóa. KHÔNG có rủi ro deadlock MỚI từ việc
này: `cart_items` luôn thuộc về ĐÚNG 1 user (`user_id` cố định trong filter),
2 user khác nhau không bao giờ tranh chấp khóa `cart_items` của nhau.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemRead, OrderRead

# State machine cho PUT /orders/{id}/status (Admin, task 3.4.2) - transition
# HỢP LỆ DUY NHẤT được phép qua endpoint này. Set rỗng = trạng thái CUỐI
# (terminal) - không cho chuyển đi đâu nữa qua endpoint thường (VD muốn "mở
# lại" 1 đơn đã delivered/cancelled cần thao tác khác, không phải chuyện 1
# dòng PUT thông thường nên cho phép ngầm).
#
# Cố tình KHÔNG cho phép "tự chuyển" (VD pending -> pending) - 1 request đổi
# trạng thái phải LÀ 1 bước tiến/lùi thật trong quy trình, không có ý nghĩa gì
# khi "chuyển" sang đúng trạng thái hiện tại; Admin gọi nhầm request trùng lặp
# sẽ nhận lỗi rõ ràng thay vì âm thầm coi là thành công.
VALID_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.shipping, OrderStatus.cancelled},
    OrderStatus.shipping: {OrderStatus.delivered},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}


class CheckoutError(Exception):
    """Giỏ hàng trống, hoặc 1+ sản phẩm không đủ tồn kho/ngừng bán tại thời
    điểm khóa (dù lúc thêm vào giỏ trước đó đủ) - router dịch sang 409."""


class CancelNotAllowedError(Exception):
    """Đơn hàng không ở trạng thái cho phép hủy - router dịch sang 400."""


class InvalidStatusTransitionError(Exception):
    """Chuyển trạng thái không hợp lệ theo `VALID_STATUS_TRANSITIONS` - router
    dịch sang 400."""


def _to_order_item_read(item: OrderItem) -> OrderItemRead:
    return OrderItemRead(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product_name,
        quantity=item.quantity,
        price_at_purchase=item.price_at_purchase,
    )


def _to_order_read(order: Order, items: list[OrderItem]) -> OrderRead:
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_amount=order.total_amount,
        shipping_name=order.shipping_name,
        shipping_address=order.shipping_address,
        shipping_phone=order.shipping_phone,
        note=order.note,
        items=[_to_order_item_read(item) for item in items],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def to_order_read_single(db: Session, order: Order) -> OrderRead:
    """Dùng cho 1 đơn ĐƠN LẺ (chi tiết, sau khi tạo/hủy/đổi trạng thái) - 1
    query phụ lấy order_items của ĐÚNG đơn này là đủ, không cần batch (batch
    chỉ cần thiết cho danh sách nhiều đơn cùng lúc, xem `list_orders` bên
    dưới - tránh N+1 ở TRƯỜNG HỢP ĐÓ, không phải ở đây)."""
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    return _to_order_read(order, items)


def get_order_by_id(db: Session, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def list_orders(
    db: Session,
    *,
    page: int,
    page_size: int,
    user_id: int | None,
    status_filter: OrderStatus | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None = None,
) -> tuple[list[OrderRead], int]:
    """`user_id=None` - dùng cho Admin (mọi user); `user_id=<id>` - dùng cho
    Customer (chỉ đơn của chính họ, xem `GET /orders`).

    Batch-load `order_items` cho CẢ TRANG bằng 1 query `WHERE order_id IN
    (...)` (KHÔNG dùng `relationship()`, cùng convention `product_service.py`)
    - tránh N+1 (1 query cho order_items của TOÀN BỘ trang, không phải 1
    query/đơn hàng).

    `search` (task 4.4.2, Admin - `GET /orders/admin`) - hệ thống KHÔNG có
    field mã đơn hàng dạng chữ (VD "VUN001") ở bất kỳ đâu, chỉ có `id` số
    thuần - "tìm theo mã đơn hàng" ở UI thực chất là tìm theo `id`, hiển thị
    cosmetic thành "#123". Parse: bỏ tiền tố "#" hoặc "VUN" (không phân biệt
    hoa/thường) nếu có, phần còn lại toàn số -> so khớp CHÍNH XÁC `Order.id`;
    ngược lại (không phải số) -> tìm theo `Order.shipping_name` (tên khách
    nhận hàng lúc đặt, KHÔNG phải `users.full_name` - cùng lý do snapshot đã
    ghi ở `orders.shipping_name`, task 4.3.2).
    """
    query = db.query(Order)
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    if status_filter is not None:
        query = query.filter(Order.status == status_filter)
    if date_from is not None:
        query = query.filter(Order.created_at >= date_from)
    if date_to is not None:
        # +1 ngày, so sánh "<" - để NGÀY date_to được tính TRỌN VẸN (đơn tạo
        # lúc 23:59 ngày date_to vẫn phải nằm trong kết quả) - so sánh "<=
        # date_to" (không cộng thêm) sẽ hiểu ngầm là "< date_to 00:00:00",
        # LOẠI TRỪ nhầm toàn bộ ngày date_to.
        query = query.filter(Order.created_at < date_to + timedelta(days=1))
    if search:
        stripped = search.strip()
        if stripped.lower().startswith("vun"):
            stripped = stripped[3:]
        elif stripped.startswith("#"):
            stripped = stripped[1:]
        if stripped.isdigit():
            query = query.filter(Order.id == int(stripped))
        else:
            query = query.filter(Order.shipping_name.ilike(f"%{search.strip()}%"))

    total = query.count()
    orders = query.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    order_ids = [order.id for order in orders]
    items_by_order_id: dict[int, list[OrderItem]] = {oid: [] for oid in order_ids}
    if order_ids:
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all():
            items_by_order_id[item.order_id].append(item)

    reads = [_to_order_read(order, items_by_order_id[order.id]) for order in orders]
    return reads, total


def checkout(db: Session, user: User, payload: OrderCreate) -> Order:
    """Đặt hàng từ TOÀN BỘ giỏ hàng hiện tại - xem giải thích đầy đủ về khóa
    (thứ tự, đối tượng khóa) ở docstring module.
    """
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id).with_for_update().all()
    if not cart_items:
        raise CheckoutError("Giỏ hàng trống - không có gì để đặt")

    # Khóa products theo thứ tự product_id TĂNG DẦN - xem lý do ở docstring module.
    product_ids = sorted({item.product_id for item in cart_items})
    products_by_id = {
        pid: db.query(Product).filter(Product.id == pid).with_for_update().one() for pid in product_ids
    }

    # Kiểm tra LẠI (dưới khóa - thấy đúng giá trị mới nhất đã commit, không
    # phải giá trị đọc lúc thêm vào giỏ trước đó, có thể đã lỗi thời) - gom
    # ĐỦ mọi sản phẩm thiếu vào 1 thông báo, không dừng ở lỗi đầu tiên, để
    # khách biết chính xác cần bỏ/giảm sản phẩm nào.
    problems: list[str] = []
    for item in cart_items:
        product = products_by_id[item.product_id]
        if not product.is_active:
            problems.append(f'"{product.name}" không còn kinh doanh')
        elif product.stock_quantity < item.quantity:
            problems.append(f'"{product.name}" chỉ còn {product.stock_quantity} (giỏ hàng: {item.quantity})')

    if problems:
        db.rollback()
        raise CheckoutError("Không thể đặt hàng: " + "; ".join(problems))

    order = Order(
        user_id=user.id,
        status=OrderStatus.pending,
        total_amount=Decimal("0"),
        shipping_name=payload.shipping_name,
        shipping_address=payload.shipping_address,
        shipping_phone=payload.shipping_phone,
        note=payload.note,
    )
    db.add(order)
    db.flush()  # order.id có giá trị để gán cho order_items, CHƯA commit

    total_amount = Decimal("0")
    for item in cart_items:
        product = products_by_id[item.product_id]
        product.stock_quantity -= item.quantity
        total_amount += product.price * item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                price_at_purchase=product.price,
            )
        )
        db.delete(item)

    order.total_amount = total_amount
    db.commit()
    db.refresh(order)
    return order


def _restock_order_items(db: Session, order: Order) -> None:
    """Hoàn lại `stock_quantity` cho mọi sản phẩm trong đơn - dùng chung cho
    CẢ 2 đường hủy đơn (`cancel_order` do Customer, `update_status` do Admin
    đổi sang "cancelled") để tránh lệch hành vi giữa 2 đường (nếu chỉ
    `cancel_order` hoàn kho còn Admin đổi trạng thái không hoàn, tồn kho sẽ
    "mất" vĩnh viễn cho đơn Admin hủy qua đường kia - bug thật, không phải lý
    thuyết). Cũng khóa theo thứ tự `product_id` tăng dần, cùng lý do tránh
    deadlock đã giải thích ở `checkout()`.
    """
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    product_ids = sorted({item.product_id for item in items})
    products_by_id = {
        pid: db.query(Product).filter(Product.id == pid).with_for_update().one() for pid in product_ids
    }
    for item in items:
        products_by_id[item.product_id].stock_quantity += item.quantity


def cancel_order(db: Session, order: Order) -> None:
    """Chỉ cho hủy khi đơn còn `pending` - QUYẾT ĐỊNH có chủ đích: 1 khi Admin
    đã `confirmed`/`shipping` nghĩa là quy trình xử lý/giao hàng thật đã bắt
    đầu (có thể đã đóng gói, đã giao cho đơn vị vận chuyển) - hủy tự động ở
    bước đó cần phối hợp nghiệp vụ ngoài phạm vi hệ thống (hoàn hàng vật lý,
    liên hệ đơn vị giao hàng...), không phải chỉ đổi 1 field DB. Giữ đơn giản
    nhất cho phạm vi đồ án: Customer tự hủy được CHỈ khi đơn CHƯA được xử lý.

    Hoàn kho khi hủy - đơn `pending` đã trừ kho lúc checkout nhưng chưa thật
    sự "bán" (chưa xác nhận/giao) - không hoàn kho sẽ khiến tồn kho bị mất
    vĩnh viễn cho đơn không thành.
    """
    if order.status != OrderStatus.pending:
        raise CancelNotAllowedError(
            f'Chỉ có thể hủy đơn ở trạng thái "pending" (đơn hiện tại: "{order.status.value}")'
        )

    _restock_order_items(db, order)
    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)


def update_order_status(db: Session, order: Order, new_status: OrderStatus) -> None:
    """Admin đổi trạng thái đơn - validate theo `VALID_STATUS_TRANSITIONS`
    (state machine CƠ BẢN: pending -> confirmed/cancelled, confirmed ->
    shipping/cancelled, shipping -> delivered, delivered/cancelled không
    chuyển tiếp được nữa qua endpoint này) - 400 rõ ràng (liệt kê đúng những
    trạng thái ĐƯỢC PHÉP chuyển tới) nếu Admin cố chuyển sai quy tắc, KHÔNG
    âm thầm chấp nhận mọi giá trị.

    RIÊNG trường hợp đổi sang "cancelled" - áp dụng ĐÚNG cơ chế hoàn kho như
    `cancel_order()` (dùng chung `_restock_order_items`) - tránh lệch hành vi
    giữa 2 đường hủy đơn (Customer tự hủy vs Admin hủy hộ), xem giải thích ở
    `_restock_order_items`.
    """
    allowed = VALID_STATUS_TRANSITIONS[order.status]
    if new_status not in allowed:
        if not allowed:
            raise InvalidStatusTransitionError(
                f'Đơn hàng đã ở trạng thái cuối "{order.status.value}" - '
                "không thể chuyển sang trạng thái khác qua endpoint này"
            )
        allowed_text = ", ".join(sorted(s.value for s in allowed))
        raise InvalidStatusTransitionError(
            f'Không thể chuyển từ "{order.status.value}" sang "{new_status.value}" - '
            f"chỉ được chuyển sang: {allowed_text}"
        )

    if new_status == OrderStatus.cancelled:
        _restock_order_items(db, order)

    order.status = new_status
    db.commit()
    db.refresh(order)
