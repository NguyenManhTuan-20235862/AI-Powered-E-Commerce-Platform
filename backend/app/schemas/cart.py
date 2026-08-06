"""Pydantic schemas: Cart (task 3.4.2) - viết lại hoàn toàn từ placeholder cũ,
khớp model `CartItem` thật (task 3.1.3)."""

from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class CartItemCreate(BaseModel):
    product_id: int
    # le=1000 - chặn giá trị vô lý (không phải giới hạn nghiệp vụ thật, chỉ
    # validate input cơ bản) - giới hạn tồn kho thật (stock_quantity) mới là
    # ràng buộc chính, kiểm tra ở tầng service.
    quantity: int = Field(default=1, ge=1, le=1000)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=1000)


class CartItemRead(BaseSchema):
    """1 dòng trong giỏ - LỒNG SẴN thông tin sản phẩm cần cho hiển thị (tên,
    ảnh, giá, tồn kho hiện tại) - JOIN thẳng `products` (KHÔNG dùng
    `relationship()`, cùng convention đã dùng ở `product_service.py`).

    `stock_quantity`/`is_active` (tồn kho THẬT hiện tại, is_active THẬT hiện
    tại của sản phẩm - KHÔNG phải lúc thêm vào giỏ) - để Frontend CẢNH BÁO
    nếu sản phẩm trong giỏ đã hết hàng/ngừng bán SAU KHI khách đã thêm vào
    (VD Admin sửa tồn kho hoặc ẩn sản phẩm trong lúc khách đang giữ giỏ hàng)
    - KHÔNG trừ kho ở bước này (trừ kho thật chỉ xảy ra lúc checkout,
    `POST /orders`, có `SELECT ... FOR UPDATE` thật - task 3.4.2/8.2).
    """

    id: int
    product_id: int
    product_name: str
    product_slug: str
    product_image_url: str | None = None
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    stock_quantity: int
    is_active: bool


class CartRead(BaseSchema):
    items: list[CartItemRead] = []
    total_amount: Decimal = Decimal("0")
