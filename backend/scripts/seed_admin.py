"""Seed 1 tài khoản admin — dùng đúng cơ chế hash thật của app (bcrypt qua
`app.core.security.hash_password`), KHÔNG insert password plain text bằng SQL
thô (mất tính năng hash + không nhất quán với luồng /auth/register thật).

Idempotent: nếu email đã tồn tại thì chỉ cập nhật password_hash + role=admin
(không tạo trùng, không lỗi UNIQUE constraint khi chạy lại nhiều lần).

Đọc DATABASE_URL từ `backend/.env` (giống mọi entrypoint khác của app, qua
`app.core.config.get_settings()`) — KHÔNG hardcode connection string riêng ở
đây, tránh lệch với cấu hình thật đang dùng.

Cách chạy: xem hướng dẫn trong docs/KNOWN_TODOS.md hoặc lệnh đã dùng để
verify task 2.3.1 (chạy trong container backend dev image, trỏ DATABASE_URL
tới MySQL qua host.docker.internal hoặc tên service `mysql` khi Backend đã
vào docker-compose.yml ở task 2.3.4).

Biến môi trường tuỳ chỉnh (đều có default để chạy nhanh lúc dev):
    ADMIN_EMAIL      (default: admin@example.com)
    ADMIN_PASSWORD   (default: Admin@123)
    ADMIN_FULL_NAME  (default: Admin)
"""

import os

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def seed_admin() -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "Admin@123")
    full_name = os.getenv("ADMIN_FULL_NAME", "Admin")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=UserRole.admin,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Đã tạo admin mới: {email} (id sẽ hiện sau lần query kế tiếp)")
        else:
            user.password_hash = hash_password(password)
            user.role = UserRole.admin
            user.is_active = True
            db.commit()
            print(f"Đã cập nhật admin đã tồn tại: {email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
