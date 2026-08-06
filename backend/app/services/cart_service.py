"""Business logic: Cart (task 3.4.2) - tách khỏi router app/routers/cart.py.

Cùng convention với `product_service.py`/`auth_service.py`: router chịu
trách nhiệm 404 (lookup đơn giản, tự query rồi check None) - service raise
`CartError` (business rule thật sự cần tính toán, VD kiểm tra tồn kho) cho
router dịch sang 400.

CHỈ CẢNH BÁO tồn kho ở đây (giỏ hàng), CHƯA trừ kho thật - trừ kho thật + khóa
dòng chỉ xảy ra lúc checkout (`app/services/order_service.py:checkout`,
`SELECT ... FOR UPDATE` thật, task 3.4.2/8.2). Giỏ hàng đủ tồn kho tại thời
điểm THÊM VÀO GIỎ không đảm bảo còn đủ tại thời điểm ĐẶT HÀNG (người khác có
thể mua trước) - đây chính là lý do checkout phải tự kiểm tra lại lần nữa
dưới khóa, không tin vào việc đã pass check ở bước thêm giỏ.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemRead, CartRead


class CartError(Exception):
    """Lỗi nghiệp vụ giỏ hàng (sản phẩm không tồn tại/ngừng bán/không đủ tồn
    kho) - router dịch sang HTTPException 400."""


def _to_cart_item_read(item: CartItem, product: Product) -> CartItemRead:
    return CartItemRead(
        id=item.id,
        product_id=product.id,
        product_name=product.name,
        product_slug=product.slug,
        product_image_url=product.image_url,
        unit_price=product.price,
        quantity=item.quantity,
        subtotal=product.price * item.quantity,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
    )


def get_cart(db: Session, user_id: int) -> CartRead:
    """JOIN thẳng `products` (KHÔNG dùng `relationship()`, xem
    `product_service.py`) - 1 query duy nhất cho cả giỏ hàng, không N+1."""
    rows = (
        db.query(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.id)
        .all()
    )
    items = [_to_cart_item_read(item, product) for item, product in rows]
    total_amount = sum((item.subtotal for item in items), Decimal("0"))
    return CartRead(items=items, total_amount=total_amount)


def get_own_cart_item(db: Session, user_id: int, item_id: int) -> CartItem | None:
    """Lookup 1 dòng giỏ hàng CỦA ĐÚNG user này - `user_id` nằm NGAY TRONG
    filter (không phải check riêng sau khi load) nên tự nhiên loại trừ việc 1
    user thao tác lên dòng giỏ hàng của người khác (đoán `item_id`) - khác
    Order (cần check `order.user_id == current_user.id` RIÊNG sau khi load,
    vì Admin còn cần xem được đơn của Customer khác) - `cart_items` không có
    khái niệm Admin xem giỏ người khác, nên lồng thẳng vào filter là đủ và
    gọn hơn.
    """
    return db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user_id).first()


def add_item(db: Session, user_id: int, product_id: int, quantity: int) -> None:
    """Thêm sản phẩm vào giỏ - CỘNG DỒN quantity nếu sản phẩm ĐÃ có trong giỏ
    (hành vi UX chuẩn: bấm "Thêm vào giỏ" lần 2 cho cùng 1 sản phẩm = tăng số
    lượng, KHÔNG báo lỗi trùng, KHÔNG tạo dòng mới) - khớp đúng
    UNIQUE (user_id, product_id) đã thiết kế ở DB (task 3.1.3).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None or not product.is_active:
        raise CartError("Sản phẩm không tồn tại hoặc đã ngừng kinh doanh")

    existing = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .first()
    )
    new_quantity = (existing.quantity if existing else 0) + quantity
    if new_quantity > product.stock_quantity:
        raise CartError(f'Chỉ còn {product.stock_quantity} sản phẩm "{product.name}" trong kho')

    if existing is not None:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(user_id=user_id, product_id=product_id, quantity=new_quantity))
    db.commit()


def update_item_quantity(db: Session, item: CartItem, quantity: int) -> None:
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product is None or not product.is_active:
        raise CartError("Sản phẩm không còn kinh doanh - vui lòng xóa khỏi giỏ")
    if quantity > product.stock_quantity:
        raise CartError(f'Chỉ còn {product.stock_quantity} sản phẩm "{product.name}" trong kho')

    item.quantity = quantity
    db.commit()


def remove_item(db: Session, item: CartItem) -> None:
    db.delete(item)
    db.commit()


def clear_cart(db: Session, user_id: int) -> None:
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()
