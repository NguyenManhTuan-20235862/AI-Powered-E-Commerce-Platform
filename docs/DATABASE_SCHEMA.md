# Database Schema — MySQL

**Task WBS:** 1.3.1 — Thiết kế bảng User + role
**Phạm vi:** Chỉ bảng `users` (các bảng Product, Order, Category... sẽ bổ sung ở task 3.1)
**Công nghệ:** MySQL 8, SQLAlchemy 2.0 (ORM), Alembic (migration)

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

## Quan hệ với các bảng khác (sẽ hoàn thiện ở task 3.1)

- `users.id` → được tham chiếu bởi `orders.user_id` (1 user có nhiều order)
- `users.id` → được tham chiếu bởi review trong MongoDB (lưu `user_id` dạng field thường, không phải FK vì khác hệ CSDL)

---

## Ghi chú

- File này hiện chỉ cover bảng `users` đúng phạm vi task 1.3.1. Khi làm task 3.1 (thiết kế schema Product/Order/Category), nên mở rộng file này thành `DATABASE_SCHEMA.md` đầy đủ thay vì tạo file rời rạc, để giữ 1 nguồn tham chiếu duy nhất — tương tự cách `docs/API_SPEC.md` đang được dùng cho toàn bộ endpoint.
- Migration đầu tiên (Alembic) nên tạo đúng theo bảng này ở task 1.3.1, tránh sinh cột thừa rồi phải sửa lại ở task 3.1.4.
