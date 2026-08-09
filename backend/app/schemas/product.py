"""Pydantic schemas: Product (request & response models, task 3.4.1).

Viết lại HOÀN TOÀN từ đầu - schema cũ (trước task này) là placeholder lệch
hẳn model `Product` thật (task 3.1.2): sai kiểu dữ liệu `id`/`category_id`
(khai `str` thay vì `int`), thiếu `is_active`/`slug`, sai tên field `stock`
(đúng tên cột là `stock_quantity`) - xem `docs/KNOWN_TODOS.md` #14. File này
là nguồn thay thế hoàn toàn, không kế thừa/vá lại bất kỳ phần nào của bản cũ.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class CategorySummary(BaseSchema):
    """Thông tin danh mục TỐI GIẢN lồng trong `ProductRead` - xem giải thích
    đánh đổi denormalize ở docstring `ProductRead` bên dưới."""

    id: int
    name: str


class ProductBase(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=255)
    # Optional - nếu không truyền, tự sinh từ `name` (xem
    # app/services/product_service.py: slugify()/generate_unique_slug()).
    # DÙ có truyền tay, vẫn bị chuẩn hóa qua slugify() (bỏ dấu tiếng Việt, chữ
    # thường, khoảng trắng/ký tự đặc biệt -> dấu gạch ngang) - đảm bảo LUÔN
    # URL-safe bất kể nguồn nhập, không cần validate riêng bằng regex ở đây.
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    # gt=0 - giá bán phải dương (ràng buộc nghiệp vụ hợp lý, DB không tự
    # enforce vì cột price không có CHECK constraint, xem
    # docs/DATABASE_SCHEMA.md mục products).
    price: Decimal = Field(gt=0)
    image_url: str | None = Field(default=None, max_length=500)


class ProductCreate(ProductBase):
    """Payload tạo sản phẩm mới (Admin). `stock_quantity` CÓ mặt ở đây (khởi
    tạo tồn kho ban đầu) - khác `ProductUpdate` (xem giải thích ở đó vì sao
    KHÔNG cho sửa qua PUT thông thường)."""

    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Payload cập nhật sản phẩm (Admin, PUT) - toàn bộ field optional (partial
    update, field không truyền = giữ nguyên, xem
    `app/services/product_service.py:update_product` dùng `exclude_unset`).

    CỐ TÌNH KHÔNG có `stock_quantity` ở đây - đã cân nhắc rủi ro race
    condition (task 3.4.1, được hỏi rõ trong yêu cầu): PUT thông thường ghi
    theo kiểu "SET stock_quantity = giá_trị_mới" (overwrite tuyệt đối, không
    dựa vào giá trị hiện tại) - khác hẳn bản chất "trừ kho" lúc checkout (task
    8.2, SELECT FOR UPDATE khóa dòng, thao tác TƯƠNG ĐỐI dựa trên giá trị đọc
    được). Nếu Admin sửa tồn kho CÙNG lúc có khách đang checkout sản phẩm đó,
    UPDATE nào commit SAU sẽ ghi đè hoàn toàn UPDATE trước đó ("lost update") -
    VD: tồn kho thật = 10, khách checkout trừ còn 8 (dựa trên đọc = 10 trước
    đó); nếu ngay lúc đó Admin sửa tồn kho thành 50 (đếm kho thủ công) rồi
    commit SAU transaction checkout, kết quả cuối = 50 (mất hẳn hiệu lực của
    giao dịch trừ kho, dù giao dịch đó đã "thành công" trả về client).

    ĐÂY KHÔNG PHẢI race condition kiểu task 8.2 (nhiều khách concurrent trừ
    kho cùng lúc, tần suất CAO, cần SELECT FOR UPDATE) - sửa tồn kho bằng tay
    của Admin là thao tác tần suất THẤP (1 người, không đông đúc) nên bản
    thân việc 2 Admin cùng sửa lúc va chạm nhau gần như không đáng lo. Rủi ro
    thật nằm ở chỗ KHÁC: 1 endpoint "SET tuyệt đối" cho 1 cột mà nghiệp vụ
    khác (checkout) đang thao tác TƯƠNG ĐỐI trên cùng cột đó, dễ vô tình xóa
    sạch hiệu lực của giao dịch đang chạy dở dù tần suất Admin sửa thấp.
    Quyết định: KHÔNG cho sửa `stock_quantity` qua PUT thông thường ở task
    này - để dành 1 cơ chế riêng (VD `PATCH /products/{id}/stock` nhận DELTA
    thay vì giá trị tuyệt đối, dùng chung `SELECT FOR UPDATE` với task 8.2)
    khi thật sự cần - xem `docs/KNOWN_TODOS.md`.
    """

    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProductRead(BaseSchema):
    """Response công khai - khớp CHÍNH XÁC model `Product` thật (task 3.1.2).

    `category` LỒNG SẴN (id + name, không chỉ `category_id` trơ) - đánh đổi
    đã cân nhắc:
    - Chỉ `category_id`: 0 chi phí DB thêm, nhưng Frontend phải tự gọi thêm
      `GET /categories` rồi tự map category_id -> tên ở phía client cho MỌI
      trang hiển thị sản phẩm (list/detail/related) - round-trip + logic
      thừa phía Frontend cho thứ thuần hiển thị.
    - Lồng sẵn `{id, name}` (đã chọn): JOIN thẳng bảng `categories` trong
      CÙNG 1 câu query (xem `app/services/product_service.py` - KHÔNG dùng
      SQLAlchemy `relationship()`, model `Product`/`Category` cố tình không
      khai báo quan hệ ORM, giữ đúng convention tối giản đã dùng xuyên suốt
      dự án) - vẫn CHỈ 1 query cho cả trang (không N+1: JOIN 1 lần cho toàn
      bộ danh sách, không phải query category riêng cho từng sản phẩm).
      Chi phí thêm gần như 0 (category_id đã có index, JOIN theo khóa chính/
      khóa ngoại có index rất rẻ ở MySQL) - đổi lại UX tốt hơn hẳn, không cần
      round-trip phụ phía Frontend.
    """

    id: int
    category: CategorySummary
    name: str
    slug: str
    description: str | None = None
    price: Decimal
    stock_quantity: int
    image_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductImageRead(BaseModel):
    image_url: str
