# Database Schema — MySQL & MongoDB

**Task WBS:** 1.3.1 (bảng `users`) + 3.1.1 (ERD đầy đủ, dbdiagram.io) + 3.1.2
(model Category/Product) + 3.1.3 (model CartItem/Order/OrderItem/Payment) +
3.1.4 (Alembic migration) + 3.2.1 (collection MongoDB `chat_logs`) + 3.2.2
(collection MongoDB `reviews`) + 3.5.1 (collection MongoDB `product_catalog_sync`)
**Phạm vi:** Đủ 7 bảng MySQL — `users`, `categories`, `products`, `cart_items`,
`orders`, `order_items`, `payments` — VÀ 3 collection MongoDB — `chat_logs`,
`reviews`, `product_catalog_sync`
**Công nghệ:** MySQL 8, SQLAlchemy 2.0 (ORM), Alembic (migration) cho phần
quan hệ; MongoDB (PyMongo) cho phần phi cấu trúc
**Model code thật:** `app/models/user.py`, `category.py`, `product.py`, `cart.py`,
`order.py` (Order/OrderItem/Payment cùng file) cho MySQL — `app/schemas/chat_log.py`
(Pydantic, KHÔNG phải SQLAlchemy — MongoDB không có ORM quan hệ) cho `chat_logs`.
File này là tài liệu SCHEMA (cột/field/ràng buộc/index/lý do nghiệp vụ), KHÔNG
lặp lại toàn bộ code Python cho 6 bảng MySQL mới + collection MongoDB (khác
cách trình bày bảng `users` bên dưới, viết từ trước khi có code thật) để tránh
2 nguồn dễ lệch nhau — code trong `app/models/`/`app/schemas/chat_log.py` mới
là nguồn chính thức, sửa gì thì đồng bộ lại bảng ở đây.

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

## MongoDB Collections

MongoDB **không có FK/CHECK constraint thật** như MySQL — mọi ràng buộc kiểu
dữ liệu chỉ enforce ở tầng ứng dụng (Pydantic, `app/schemas/`), MongoDB tự nó
chấp nhận bất kỳ document nào (schema-less). Các mục "FOREIGN KEY" bên dưới vì
vậy chỉ mang tính THAM CHIẾU LOGIC (field thường trỏ tới ID ở nơi khác), khác
hẳn ý nghĩa "FOREIGN KEY" ở phần MySQL phía trên — xem giải thích chi tiết ở
từng collection.

### Collection `chat_logs` (task 3.2.1)

**Quyết định thiết kế: 1 document / 1 TIN NHẮN** (không phải 1 document / 1
session với mảng `messages` lồng bên trong). Lý do đầy đủ xem docstring
`app/schemas/chat_log.py`, tóm tắt:
- Insert khớp tự nhiên với luồng ghi thật (mỗi tin nhắn tới → insert ngay,
  không cần find-rồi-`$push` vào document session đang có).
- Tránh rủi ro vượt giới hạn cứng 16MB/document của MongoDB nếu 1 session chat
  rất dài.
- Query lịch sử theo user (`GET /ai/chat/history`) và Admin duyệt toàn bộ log
  (`GET /ai/chat/logs`) đều là query PHẲNG trên field top-level (`user_id`,
  `session_id`, `created_at`) — không cần `$unwind` aggregation như khi dữ
  liệu nằm trong mảng lồng.
- `session_id` vẫn dùng để GOM NHÓM tin nhắn cùng 1 phiên (query
  `{session_id: ...}` sort theo `created_at`) — chỉ là field thường trên từng
  document, không phải cấu trúc lồng vật lý.

| Field | Kiểu dữ liệu | Bắt buộc? | Mô tả |
|---|---|---|---|
| `_id` | `ObjectId` | Tự sinh | Định danh document, MongoDB tự tạo lúc insert |
| `user_id` | `Int64` (khớp `BIGINT` của `users.id` bên MySQL) | NOT NULL | Chủ hội thoại — xem mục "Tham chiếu logic" bên dưới |
| `session_id` | `String` | NOT NULL | Nhóm các tin nhắn cùng 1 phiên chat — do tầng service sinh (VD `uuid4`), 1 user có thể có nhiều session theo thời gian |
| `role` | `String` — `"user"` \| `"assistant"` \| `"system"` \| `"tool"` | NOT NULL | Ai gửi tin nhắn — 2 giá trị đầu dùng ngay ở task 3.2.1, `"system"`/`"tool"` để sẵn cho task 6.3 (tool calling) |
| `message` | `String` | NOT NULL | Nội dung tin nhắn (text) |
| `metadata` | `Object` (linh hoạt, không cố định field con) | NULLABLE | VD: sản phẩm AI gợi ý kèm tin nhắn, `tool_calls` (task 6.3), thông tin model/token — cấu trúc con quyết định khi có code AI Agent thật |
| `created_at` | `Date` (UTC) | NOT NULL | Thời điểm tạo tin nhắn |

### Index đề xuất (task 3.2.1 — CHỈ liệt kê, CHƯA tạo thật)

Chưa chạy `create_index()` thật ở task này (collection còn chưa tồn tại — lazy
create khi có write đầu tiên, xem task 2.3.2) — để task 3.2.3 (kết nối PyMongo
thật) tạo cùng lúc với code kết nối, tránh tạo index cho collection chưa có
document nào:

- **`(user_id, created_at)`** — chính, phục vụ `GET /ai/chat/history` (lịch sử
  của 1 user, sort theo thời gian, phân trang).
- **`(session_id, created_at)`** — dựng lại đúng thứ tự hội thoại trong 1
  session (gom nhóm theo `session_id`, sort theo `created_at`).
- **`(created_at)`** riêng — phục vụ Admin duyệt log toàn hệ thống theo thời
  gian (`GET /ai/chat/logs`) khi KHÔNG lọc theo `user_id` cụ thể.

### Tham chiếu logic (KHÔNG phải Foreign Key thật)

- `chat_logs.user_id → users.id` (MySQL): chỉ là field thường, **KHÔNG có ràng
  buộc toàn vẹn thật giữa 2 hệ CSDL khác nhau**. Hệ quả cụ thể: xóa 1 user ở
  MySQL **KHÔNG** tự động xóa/cập nhật các document `chat_logs` liên quan —
  nếu nghiệp vụ cần giữ toàn vẹn (VD: xóa user thật thì cũng nên xóa/ẩn log
  chat của họ), phải tự xử lý ở tầng service (gọi thêm 1 lệnh
  `delete_many`/cập nhật riêng trên `chat_logs` khi xóa user) — không có cơ
  chế DB nào tự làm việc này thay cho code.
- Tương tự, `products.id`/`orders.id` (MySQL) CÓ THỂ được tham chiếu trong
  `metadata` (VD sản phẩm AI gợi ý) — cùng tính chất tham chiếu logic, không
  phải FK thật.

### Collection `reviews` (task 3.2.2)

**Quyết định thiết kế 1 — denormalize `user_name`** (snapshot tên user lúc
viết review, không chỉ lưu `user_id` rồi join ngược MySQL): tránh N+1/batch
query sang MySQL chỉ để lấy tên hiển thị mỗi lần load trang review của 1 sản
phẩm. Đánh đổi: nếu user đổi `full_name` sau khi đã review, review CŨ vẫn
hiển thị tên CŨ (không tự đồng bộ) — **chấp nhận độ lệch này**, KHÔNG xây cơ
chế đồng bộ (event/job nghe đổi tên rồi `update_many`) vì chi phí xây/bảo trì
không tương xứng lợi ích cho dự án đồ án solo. Xem phân tích đầy đủ ở
docstring `app/schemas/review.py`.

**Quyết định thiết kế 2 — soft-delete (`is_deleted`) thay vì xóa cứng** khi
Admin gọi `DELETE /reviews/{review_id}`: KHÁC lý do soft-delete của
`products.is_active` (ràng buộc toàn vẹn thật — `order_items` vẫn cần tham
chiếu sản phẩm cũ). Review không có bảng nào tham chiếu ngược `reviews.id` —
lý do soft-delete ở đây là MODERATION: giữ audit trail (Admin nào xóa gì) +
cho phép undo nếu xóa nhầm, đánh đổi lại là mọi query công khai phải nhớ lọc
`is_deleted: false` (tập trung trong 1 hàm repository dùng chung, task 6.x,
không rải rác). `is_deleted` là field NỘI BỘ — không xuất hiện trong response
API công khai (`ReviewRead`), chỉ có ở document raw (`ReviewInDB`).

| Field | Kiểu dữ liệu | Bắt buộc? | Mô tả |
|---|---|---|---|
| `_id` | `ObjectId` | Tự sinh | Định danh document |
| `product_id` | `Int64` (khớp `BIGINT` của `products.id` bên MySQL) | NOT NULL | Sản phẩm được review |
| `user_id` | `Int64` (khớp `BIGINT` của `users.id` bên MySQL) | NOT NULL | Người viết review |
| `user_name` | `String` | NOT NULL | Tên user — DENORMALIZE, snapshot lúc viết (xem quyết định thiết kế 1) |
| `order_id` | `Int64` (khớp `BIGINT` của `orders.id` bên MySQL) | NOT NULL | Đơn hàng chứng minh đã mua — bắt buộc vì `POST /products/{id}/reviews` chỉ cho viết khi đã mua (`docs/API_SPEC.md` mục 7), không có luồng review chưa xác minh |
| `rating` | `Int32` | NOT NULL, 1–5 | Số sao đánh giá |
| `comment` | `String` | NULLABLE | Nội dung review |
| `images` | `Array<String>` (URL) | NULLABLE | Ảnh review — để ngỏ mở rộng, chưa có route upload thật trong repo |
| `is_verified_purchase` | `Boolean` | NOT NULL, mặc định `true` | Luôn `true` với dữ liệu hợp lệ hiện tại (suy ra từ `order_id` bắt buộc) — giữ tường minh để đọc trực tiếp + forward-compatible nếu nghiệp vụ đổi sau này |
| `is_deleted` | `Boolean` | NOT NULL, mặc định `false` | Cờ soft-delete nội bộ (xem quyết định thiết kế 2) — KHÔNG lộ ra response API công khai |
| `created_at` | `Date` (UTC) | NOT NULL | Thời điểm viết review |
| `updated_at` | `Date` (UTC) | NULLABLE | Thời điểm cập nhật gần nhất (VD Admin soft-delete) |

### Index đề xuất — `reviews` (task 3.2.2 — CHỈ liệt kê, CHƯA tạo thật)

Cùng lý do chưa tạo thật như `chat_logs` (để task 3.2.3 tạo cùng lúc với code
kết nối PyMongo):

- **`(product_id, is_deleted, created_at)`** — phục vụ `GET /products/{id}/reviews`
  (lọc theo sản phẩm + loại bỏ review đã xóa mềm, sort theo thời gian). Thêm
  `is_deleted` vào giữa (không chỉ `(product_id, created_at)` như đề xuất ban
  đầu) theo nguyên tắc ESR (Equality → Sort → Range) của MongoDB — cả
  `product_id` và `is_deleted` đều là điều kiện equality trong query thật,
  đặt trước field dùng để sort (`created_at`) thì index mới được tận dụng tối
  đa.
- **`(user_id, order_id, product_id)` UNIQUE** — xác nhận đây là ràng buộc
  hợp lý: chặn 1 user gửi NHIỀU review trùng lặp cho CÙNG 1 sản phẩm TỪ CÙNG
  1 đơn hàng (spam-submit), nhưng VẪN cho phép review lại nếu mua ở đơn hàng
  KHÁC (trải nghiệm lần mua sau có thể khác). Không dùng partial filter
  (`is_deleted`) — sau khi bị Admin xóa mềm, user không viết lại được review
  cho đúng đơn hàng/sản phẩm đó nữa (chấp nhận, tránh lách luật viết bậy →
  xóa → viết bậy tiếp; có thể đổi sang partial unique index sau nếu nghiệp vụ
  cần cho "viết lại").

### Tham chiếu logic — `reviews` (KHÔNG phải Foreign Key thật)

- `reviews.product_id/order_id → products.id/orders.id`, `reviews.user_id →
  users.id` (MySQL): cùng tính chất với `chat_logs` ở trên — field thường,
  KHÔNG có ràng buộc toàn vẹn thật giữa 2 hệ CSDL. Rủi ro thực tế hiện THẤP
  vì cả 3 bảng MySQL liên quan đều KHÔNG có đường xóa cứng trong thiết kế
  hiện tại (`products`/`users` dùng soft-delete qua `is_active`,
  `orders`/`order_items` bị `ON DELETE RESTRICT` chặn xóa khi còn tham
  chiếu) — nhưng vẫn KHÔNG có gì ở tầng DB đảm bảo `product_id`/`order_id`/
  `user_id` trong 1 document `reviews` còn trỏ tới bản ghi tồn tại thật; nếu
  sau này thêm đường xóa cứng ở MySQL, phải tự xử lý đồng bộ ở tầng service.

### Collection `product_catalog_sync` (task 3.5.1)

KHÁC BẢN CHẤT với `chat_logs`/`reviews` ở trên — 2 collection đó là dữ liệu
GỐC (ghi trực tiếp), còn `product_catalog_sync` là **bản sao dẫn xuất**
(derived), đồng bộ 1 CHIỀU định kỳ từ MySQL (`products`) qua
`backend/scripts/sync_products_to_mongo.py` — nguồn sự thật vẫn luôn là
MySQL, collection này có thể xóa sạch và tái tạo lại hoàn toàn bất kỳ lúc
nào mà không mất dữ liệu. Mục đích: phục vụ AI Agent (task 6.x) truy vấn
nhanh lúc tư vấn/RAG mà không cần query trực tiếp MySQL mỗi lần.

**"Sản phẩm hot" — định nghĩa TẠM THỜI**: đồng bộ TOÀN BỘ sản phẩm
`is_active=True` (KHÔNG lọc/xếp hạng theo "bán chạy" thật — chưa có dữ liệu
tổng hợp từ `order_items` đủ dùng, task 5.3/6.x chưa tồn tại). Khi có dữ
liệu đơn hàng đủ lớn, cân nhắc thêm field điểm phổ biến vào mỗi document
thay vì thu hẹp phạm vi đồng bộ — xem đầy đủ ở docstring file script.

| Field | Kiểu dữ liệu | Bắt buộc? | Mô tả |
|---|---|---|---|
| `_id` | `Int64` — **chính là** `products.id` (MySQL), KHÔNG phải `ObjectId` | Bắt buộc | Dùng thẳng PK MySQL làm khóa Mongo — upsert đơn giản, đối chiếu ngược tức thời, không cần field phụ |
| `name` | `String` | NOT NULL | Snapshot `products.name` lúc đồng bộ |
| `slug` | `String` | NOT NULL | Snapshot `products.slug` |
| `description` | `String` | NULLABLE | Snapshot `products.description` |
| `price` | `Decimal128` (KHÔNG phải `Double`/float) | NOT NULL | Snapshot `products.price` — dùng `Decimal128` để giữ chính xác tuyệt đối cho tiền tệ, BSON không tự encode được `decimal.Decimal` của Python |
| `category_name` | `String` | NOT NULL | Tên category — DENORMALIZE (snapshot lúc đồng bộ), cùng đánh đổi đã chọn ở `reviews.user_name` (task 3.2.2), nhưng độ lệch nhỏ hơn hẳn vì job này chạy định kỳ (task 3.5.2), tự làm mới thường xuyên |
| `stock_quantity` | `Int32` | NOT NULL | Snapshot `products.stock_quantity` |
| `image_url` | `String` | NULLABLE | Snapshot `products.image_url` |
| `synced_at` | `Date` (UTC) | NOT NULL | Thời điểm lần đồng bộ GẦN NHẤT ghi document này — cập nhật ở MỌI lần chạy script, kể cả khi nội dung không đổi |

### Xử lý sản phẩm bị ẩn (`is_active=False`)

XÓA CỨNG document khỏi `product_catalog_sync` (KHÔNG soft-delete kiểu
`reviews.is_deleted`) — quyết định có chủ đích: collection này không có nhu
cầu audit trail (khác lý do soft-delete ở `reviews`), và xóa cứng đảm bảo
AI Agent RAG (task 6.x) KHÔNG THỂ gợi ý nhầm sản phẩm đã ẩn dù code truy vấn
có lỡ quên filter `is_active` hay không (document không tồn tại thì không
truy vấn ra được) — mạnh hơn cơ chế "nhớ phải filter đúng". Sản phẩm active
lại sau này tự động được đồng bộ lại ở lần chạy kế tiếp.

### Index

CHƯA đề xuất index cụ thể nào ở task 3.5.1 — khác `chat_logs`/`reviews` (đã
biết trước endpoint thật sẽ query thế nào), collection này chưa có code đọc
thật (AI Agent, task 6.x chưa tồn tại) nên chưa có cơ sở để đề xuất index
đúng nhu cầu — quyết định khi task 6.x biết rõ pattern truy vấn RAG thật.
`_id` đã có index mặc định (mọi collection Mongo), đủ cho upsert/lookup theo
ID hiện tại.

---

## Ghi chú

- File này giờ cover đủ 7 bảng MySQL theo ERD đã chốt ở task 3.1.1 (trước đó —
  task 1.3.1 — chỉ có bảng `users`) — VÀ 3 collection MongoDB `chat_logs`
  (task 3.2.1), `reviews` (task 3.2.2), `product_catalog_sync` (task 3.5.1).
- Model code thật (`app/models/`) đã tạo ở task 3.1.2 (Category, Product) và
  3.1.3 (CartItem, Order, OrderItem, Payment), đã chạy Alembic migration
  thật ở task 3.1.4 (`alembic/versions/fdf5ca1856fe_...py`, test round-trip
  upgrade→downgrade→upgrade trên MySQL thật — xem `docs/KNOWN_TODOS.md` #11
  cho 1 bug thật đã gặp + sửa trong quá trình đó).
- `CHECK (stock_quantity >= 0)` của bảng `products` đã thêm THỦ CÔNG vào
  migration Alembic (không phải autogenerate, DBML không hỗ trợ khai báo
  CHECK) ở task 3.1.4 — đã verify MySQL 8 enforce thật.
- Collection `chat_logs` (task 3.2.1) mới dừng ở THIẾT KẾ document + schema
  Pydantic tham chiếu (`app/schemas/chat_log.py`) + đề xuất index — CHƯA có
  code kết nối PyMongo thật (task 3.2.3) và CHƯA có logic ghi/đọc thật (task
  5.1 WebSocket, 6.x AI Agent) — 2 endpoint liên quan
  (`GET /ai/chat/history`, `GET /ai/chat/logs`, `app/routers/ai_chat.py`) vẫn
  đang `501`.
- Collection `reviews` (task 3.2.2) cùng tình trạng — mới THIẾT KẾ document +
  schema Pydantic (`app/schemas/review.py`, đã cập nhật từ placeholder tối
  giản trước đó — vẫn giữ tên `ReviewCreate`/`ReviewRead` để khớp import có
  sẵn ở `app/routers/review.py`, thêm mới `ReviewInDB` cho tầng service đọc
  raw document sau này) + đề xuất index — CHƯA có code kết nối PyMongo thật
  (task 3.2.3) và CHƯA có logic ghi/đọc thật hay logic verify "đã mua hàng
  chưa" (task 6.x) — cả 3 endpoint liên quan (`GET /products/{id}/reviews`,
  `POST /products/{id}/reviews`, `DELETE /reviews/{review_id}`,
  `app/routers/review.py`) vẫn đang `501`.
- Collection `product_catalog_sync` (task 3.5.1) — KHÁC 2 collection trên,
  đã có code ghi THẬT (`backend/scripts/sync_products_to_mongo.py`) — đồng
  bộ 1 chiều MySQL → Mongo, verify thật: chạy lần đầu (số document khớp số
  Product `is_active=True`), đổi giá 1 sản phẩm rồi chạy lại (Mongo cập nhật
  đúng, không tạo trùng), set `is_active=False` 1 sản phẩm rồi chạy lại
  (document tương ứng bị xóa khỏi Mongo). CHƯA lên lịch tự động chạy (task
  3.5.2, APScheduler) — hiện phải chạy tay
  (`docker compose exec backend python -m scripts.sync_products_to_mongo`).
