# Database Schema — MySQL

**Task WBS:** 1.3.1 (bảng `users`) + 3.1.1 (ERD đầy đủ, dbdiagram.io) + 3.1.2
(model Category/Product) + 3.1.3 (model CartItem/Order/OrderItem/Payment)
**Phạm vi:** Đủ 7 bảng — `users`, `categories`, `products`, `cart_items`,
`orders`, `order_items`, `payments`
**Công nghệ:** MySQL 8, SQLAlchemy 2.0 (ORM), Alembic (migration)
**Model code thật:** `app/models/user.py`, `category.py`, `product.py`, `cart.py`,
`order.py` (Order/OrderItem/Payment cùng file) — file này là tài liệu SCHEMA
(cột/ràng buộc/index/lý do nghiệp vụ), KHÔNG lặp lại toàn bộ code Python cho 6
bảng mới (khác cách trình bày bảng `users` bên dưới, viết từ trước khi có code
thật) để tránh 2 nguồn dễ lệch nhau — code trong `app/models/` mới là nguồn
chính thức, sửa gì thì đồng bộ lại bảng ở đây.

---

## Bảng `users`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh user |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEX | Dùng để đăng nhập |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Mật khẩu đã hash (bcrypt qua passlib) — **không lưu plain text** |
| `full_name` | `VARCHAR(150)` | NOT NULL | Họ tên hiển thị |
| `phone` | `VARCHAR(20)` | NULLABLE | Số điện thoại, dùng khi đặt hàng |
| `address` | `VARCHAR(500)` | NULLABLE | Địa chỉ giao hàng mặc định |
| `role` | `ENUM('customer','admin')` | NOT NULL, DEFAULT `'customer'` | Phân quyền — dùng trong middleware xác thực (task 1.3.3) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | `FALSE` = tài khoản bị khóa (Admin thao tác) |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm tạo tài khoản |
| `updated_at` | `DATETIME` | NOT NULL, `ON UPDATE CURRENT_TIMESTAMP` | Thời điểm cập nhật gần nhất |

### Index
- `UNIQUE INDEX` trên `email` — tránh trùng tài khoản, tăng tốc truy vấn khi login
- `INDEX` trên `role` — phục vụ query lọc user theo role ở trang Admin quản lý user

### Ràng buộc nghiệp vụ (áp dụng ở tầng service, không phải DB)
- Email phải hợp lệ (validate bằng `EmailStr` của Pydantic ở schema, không chỉ dựa vào DB)
- Không cho phép tự đăng ký với `role='admin'` — mặc định luôn là `customer`; muốn có admin phải seed trực tiếp hoặc do admin khác cấp quyền
- `password_hash` không bao giờ trả về trong response API (loại trừ ở Pydantic response schema)

---

## Bảng `categories`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh danh mục |
| `name` | `VARCHAR(150)` | NOT NULL | Tên danh mục hiển thị |
| `slug` | `VARCHAR(150)` | UNIQUE, NOT NULL, INDEX | Dùng cho URL (`/products?category=<slug>`) |
| `description` | `VARCHAR(500)` | NULLABLE | Mô tả ngắn danh mục |
| `parent_id` | `BIGINT` | NULLABLE, FK → `categories.id` | Danh mục cha nếu có (self-reference, cây danh mục) — NULL nếu là danh mục gốc |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm tạo danh mục |

### Index
- `UNIQUE INDEX` trên `slug` — tra cứu theo URL, tránh trùng slug

### FOREIGN KEY / ON DELETE
- `parent_id → categories.id`: **không khai báo `ON DELETE`** trong DBML (không có annotation `[delete: ...]`) — giữ hành vi mặc định của MySQL (NO ACTION/RESTRICT ngầm định), không tự suy đoán CASCADE hay SET NULL.

---

## Bảng `products`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh sản phẩm |
| `category_id` | `BIGINT` | NOT NULL, FK → `categories.id`, INDEX | Danh mục sản phẩm thuộc về |
| `name` | `VARCHAR(255)` | NOT NULL | Tên sản phẩm |
| `slug` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEX | Dùng cho URL sản phẩm |
| `description` | `TEXT` | NULLABLE | Mô tả chi tiết sản phẩm |
| `price` | `DECIMAL(12,2)` | NOT NULL | Giá bán |
| `stock_quantity` | `INT` | NOT NULL, DEFAULT `0` | Số lượng tồn kho |
| `image_url` | `VARCHAR(500)` | NULLABLE | URL ảnh sản phẩm |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE`, INDEX | `FALSE` = ẩn khỏi catalog (không xóa cứng — giữ toàn vẹn lịch sử `order_items`) |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm tạo sản phẩm |
| `updated_at` | `DATETIME` | NOT NULL, `ON UPDATE CURRENT_TIMESTAMP` | Thời điểm cập nhật gần nhất |

### Index
- `INDEX` trên `category_id`
- `INDEX` trên `is_active`
- `INDEX` composite trên `(is_active, category_id)` — query catalog thực tế (`GET /products` lọc theo category + chỉ hiện sản phẩm đang bán) luôn dùng CẢ 2 điều kiện cùng lúc, composite index phục vụ nhanh hơn 2 index đơn cộng lại (MySQL chỉ dùng được 1 index cho 1 lần quét)
- `UNIQUE INDEX` trên `slug`

### CHECK constraint (chưa áp dụng ở model — xem Ghi chú)
- `CHECK (stock_quantity >= 0)` — DBML không hỗ trợ khai báo CHECK, và model SQLAlchemy (`app/models/product.py`) **cố tình chưa khai báo** `CheckConstraint` tương ứng — sẽ thêm bằng migration Alembic riêng ở task 3.1.4, không để autogenerate tự sinh.

### Ràng buộc nghiệp vụ (áp dụng ở tầng service, không phải DB)
- Trừ kho lúc checkout dùng `SELECT ... FOR UPDATE` (khóa dòng, tránh 2 request trừ kho cùng lúc dẫn tới âm kho) — task 8.2

---

## Bảng `cart_items`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh dòng giỏ hàng |
| `user_id` | `BIGINT` | NOT NULL, FK → `users.id` | Chủ giỏ hàng |
| `product_id` | `BIGINT` | NOT NULL, FK → `products.id` | Sản phẩm trong giỏ |
| `quantity` | `INT` | NOT NULL, DEFAULT `1` | Số lượng |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm thêm vào giỏ |
| `updated_at` | `DATETIME` | NOT NULL, `ON UPDATE CURRENT_TIMESTAMP` | Thời điểm cập nhật gần nhất (đổi quantity) |

### Index
- `UNIQUE INDEX` trên `(user_id, product_id)` — 1 user không có 2 dòng cùng 1 sản phẩm; thêm sản phẩm đã có trong giỏ → tăng `quantity` dòng cũ ở tầng service, không insert dòng mới

### FOREIGN KEY / ON DELETE
- `user_id → users.id`: **`ON DELETE CASCADE`** — xóa user thì giỏ hàng liên quan tự xóa theo
- `product_id → products.id`: **`ON DELETE CASCADE`** — xóa sản phẩm thì dòng giỏ hàng liên quan tự xóa theo

Cả 2 dùng CASCADE (khác `order_items` dùng RESTRICT) vì `cart_items` chỉ là
trạng thái tạm thời, không phải dữ liệu lịch sử cần giữ lại.

---

## Bảng `orders`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh đơn hàng |
| `user_id` | `BIGINT` | NOT NULL, FK → `users.id`, INDEX | Người đặt hàng |
| `status` | `ENUM('pending','confirmed','shipping','delivered','cancelled')` | NOT NULL, DEFAULT `'pending'`, INDEX | Trạng thái đơn hàng |
| `total_amount` | `DECIMAL(12,2)` | NOT NULL | Tổng tiền đơn hàng |
| `shipping_address` | `VARCHAR(500)` | NOT NULL | Địa chỉ giao hàng (snapshot lúc đặt, không tham chiếu `users.address`) |
| `shipping_phone` | `VARCHAR(20)` | NOT NULL | SĐT nhận hàng (snapshot lúc đặt) |
| `note` | `VARCHAR(500)` | NULLABLE | Ghi chú của khách |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP`, INDEX | Thời điểm đặt hàng |
| `updated_at` | `DATETIME` | NOT NULL, `ON UPDATE CURRENT_TIMESTAMP` | Thời điểm cập nhật gần nhất (đổi status...) |

### Index
- `INDEX` trên `user_id`
- `INDEX` trên `status`
- `INDEX` trên `created_at` — dashboard doanh thu theo ngày/tuần/tháng (task 5.3)

### FOREIGN KEY / ON DELETE
- `user_id → users.id`: **`ON DELETE RESTRICT`** — order là dữ liệu lịch sử/nghiệp vụ (hóa đơn, doanh thu), không được xóa theo khi xóa user; phải xử lý nghiệp vụ khác trước (VD: khóa `is_active` thay vì xóa cứng user) nếu user đó còn đơn hàng

---

## Bảng `order_items`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh dòng chi tiết đơn hàng |
| `order_id` | `BIGINT` | NOT NULL, FK → `orders.id`, INDEX | Đơn hàng chứa dòng này |
| `product_id` | `BIGINT` | NOT NULL, FK → `products.id` | Sản phẩm được mua |
| `product_name` | `VARCHAR(255)` | NOT NULL | **Snapshot** tên sản phẩm lúc mua — phòng khi `products.name` đổi/xóa sau này |
| `quantity` | `INT` | NOT NULL | Số lượng mua |
| `price_at_purchase` | `DECIMAL(12,2)` | NOT NULL | **Snapshot** giá lúc mua — không đổi theo `products.price` |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm tạo dòng (= thời điểm đặt hàng) |

Không có `updated_at` — bản ghi lịch sử bất biến (immutable snapshot), không
có nghiệp vụ "sửa" 1 dòng `order_item` đã tạo.

### Index
- `INDEX` trên `order_id`

### FOREIGN KEY / ON DELETE
- `order_id → orders.id`: **`ON DELETE RESTRICT`**
- `product_id → products.id`: **`ON DELETE RESTRICT`**

Cả 2 dùng RESTRICT vì đây là dữ liệu lịch sử hóa đơn, không được mất/xóa theo
dù order hay product bị xóa (thực tế `products` cũng dùng `is_active=FALSE`
để ẩn thay vì xóa cứng — xem bảng `products` — nên trường hợp RESTRICT chặn
xóa product gần như không xảy ra trong vận hành bình thường).

---

## Bảng `payments`

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGINT` | PK, AUTO_INCREMENT | Định danh bản ghi thanh toán |
| `order_id` | `BIGINT` | NOT NULL, UNIQUE, FK → `orders.id` | Đơn hàng được thanh toán (quan hệ 1-1) |
| `payment_method` | `VARCHAR(50)` | NOT NULL | `vnpay`, `momo`... |
| `transaction_id` | `VARCHAR(255)` | UNIQUE, NULLABLE | Mã giao dịch từ cổng thanh toán — NULL cho tới khi cổng thanh toán trả về (bản ghi tạo trước với `status='pending'`) |
| `amount` | `DECIMAL(12,2)` | NOT NULL | Số tiền thanh toán |
| `status` | `ENUM('pending','success','failed','refunded')` | NOT NULL, DEFAULT `'pending'` | Trạng thái thanh toán |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Thời điểm tạo bản ghi thanh toán |
| `updated_at` | `DATETIME` | NOT NULL, `ON UPDATE CURRENT_TIMESTAMP` | Thời điểm cập nhật gần nhất (callback đổi status) |

### Index
- `UNIQUE INDEX` trên `order_id` — đảm bảo quan hệ 1-1 với `orders`
- `UNIQUE INDEX` trên `transaction_id` — tránh xử lý trùng khi cổng thanh toán gọi callback nhiều lần cho cùng 1 giao dịch (idempotency ở tầng DB, không chỉ ở code)

### FOREIGN KEY / ON DELETE
- `order_id → orders.id`: **`ON DELETE RESTRICT`**

---

## SQLAlchemy Model (tham khảo, sẽ hoàn thiện khi code thật ở task 1.3.1)

```python
# app/models/user.py
import enum
from sqlalchemy import BigInteger, String, Boolean, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.customer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped["datetime"] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped["datetime"] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## Quan hệ giữa các bảng (ERD, task 3.1.1)

Toàn bộ khóa ngoại trong hệ thống (khớp DBML gốc trên dbdiagram.io), kèm hành
vi `ON DELETE`:

| Quan hệ | Kiểu | `ON DELETE` | Ghi chú |
|---|---|---|---|
| `categories.parent_id → categories.id` | self-reference, N-1 | *(mặc định MySQL)* | Cây danh mục - DBML không khai báo `[delete: ...]` |
| `products.category_id → categories.id` | N-1 | *(mặc định MySQL)* | DBML không khai báo `[delete: ...]` |
| `cart_items.user_id → users.id` | N-1 | `CASCADE` | Xóa user → giỏ hàng tự xóa theo |
| `cart_items.product_id → products.id` | N-1 | `CASCADE` | Xóa sản phẩm → dòng giỏ hàng liên quan tự xóa theo |
| `orders.user_id → users.id` | N-1 | `RESTRICT` | Order là dữ liệu lịch sử, không xóa theo user |
| `order_items.order_id → orders.id` | N-1 | `RESTRICT` | Chi tiết đơn hàng là lịch sử bất biến |
| `order_items.product_id → products.id` | N-1 | `RESTRICT` | Giữ nguyên vẹn lịch sử dù sản phẩm bị ẩn/đổi |
| `payments.order_id → orders.id` | **1-1** (DBML dùng `-` thay vì `>`) | `RESTRICT` | Mỗi order tối đa 1 bản ghi thanh toán |

**"Mặc định MySQL"** = DBML không có annotation `[delete: ...]` cho quan hệ đó
→ model SQLAlchemy (`app/models/category.py`, `product.py`) cũng KHÔNG khai
báo `ondelete=` → giữ hành vi NO ACTION/RESTRICT ngầm định của InnoDB, không
tự suy đoán CASCADE hay SET NULL khi DBML không nói rõ.

Còn lại, ngoài MySQL:
- `users.id` → được tham chiếu bởi review trong MongoDB (lưu `user_id` dạng
  field thường, không phải FK vì khác hệ CSDL)
- `products.id`/`orders.id` tương tự có thể được tham chiếu bởi ChatLog
  (MongoDB, task 3.2.1) nếu AI Agent cần gợi ý theo lịch sử mua hàng — chưa
  thiết kế chi tiết, để ngỏ tới khi làm task đó.

---

## Ghi chú

- File này giờ cover đủ 7 bảng theo ERD đã chốt ở task 3.1.1 (trước đó — task
  1.3.1 — chỉ có bảng `users`).
- Model code thật (`app/models/`) đã tạo ở task 3.1.2 (Category, Product) và
  3.1.3 (CartItem, Order, OrderItem, Payment) — **CHƯA chạy Alembic migration**
  (`alembic revision --autogenerate`), cố tình dừng lại để review model trước
  khi sinh migration - đó là task 3.1.4 riêng.
- `CHECK (stock_quantity >= 0)` của bảng `products` cố tình CHƯA có trong model
  (xem mục CHECK constraint ở bảng `products` phía trên) - sẽ thêm bằng
  migration Alembic thủ công (không phải autogenerate) ở task 3.1.4.
