"""Seed dữ liệu development mẫu (vài category, vài product, 1 admin) - TÁCH
BIỆT HOÀN TOÀN khỏi Alembic migration (KHÔNG tạo/sửa schema gì ở đây, chỉ
insert dữ liệu vào bảng đã tồn tại) và khỏi dữ liệu test tạm thời tạo qua API
lúc verify tính năng (script này không xóa gì cả, chỉ thêm nếu chưa có).

KHÔNG tự chạy khi `docker compose up` (main.py/docker-entrypoint.sh không gọi
file này) - chỉ chạy THỦ CÔNG khi cần dữ liệu mẫu để phát triển/xem UI:

    docker compose exec backend python -m scripts.seed_dev_data

Idempotent - dựa trên unique key THẬT của từng bảng (`categories.slug`,
`products.slug`, `users.email` qua `seed_admin()` có sẵn - xem
docs/DATABASE_SCHEMA.md) - chạy lại nhiều lần AN TOÀN, không tạo trùng.
KHÔNG có `drop_all()`/`delete()` nào ở đây - không xóa dữ liệu cũ (kể cả dữ
liệu developer tạo qua API) trước khi seed.

Admin: dùng LẠI `scripts.seed_admin.seed_admin()` có sẵn (KHÔNG viết lại
logic hash password/idempotency riêng) - đã tự dùng đúng
`app.core.security.hash_password` (bcrypt qua passlib), KHÔNG insert plain
text.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.product import Product
from scripts.seed_admin import seed_admin

# Dữ liệu tối thiểu để xem được catalog có nội dung thật (không phải mảng
# rỗng) - KHÔNG bịa field ngoài những gì model thật yêu cầu (xem
# app/models/category.py, app/models/product.py): category chỉ cần
# name/slug/description, product cần thêm category_id (resolve qua slug bên
# dưới)/price/stock_quantity - `is_active` để mặc định model (True),
# `image_url` để trống (None, model cho phép nullable).
_CATEGORIES = [
    {"name": "Gốm sứ", "slug": "gom-su", "description": "Đồ gốm sứ thủ công"},
    {"name": "Vải dệt", "slug": "vai-det", "description": "Sản phẩm dệt may thủ công"},
    {"name": "Đồ gỗ", "slug": "do-go", "description": "Đồ nội thất/trang trí gỗ thủ công"},
]

_PRODUCTS = [
    {
        "slug": "binh-gom-hoa-van",
        "name": "Bình gốm hoa văn truyền thống",
        "category_slug": "gom-su",
        "price": Decimal("450000.00"),
        "stock_quantity": 20,
        "description": "Bình gốm thủ công, hoa văn truyền thống.",
    },
    {
        "slug": "khan-choang-len-det-tay",
        "name": "Khăn choàng len dệt tay",
        "category_slug": "vai-det",
        "price": Decimal("320000.00"),
        "stock_quantity": 15,
        "description": "Khăn choàng dệt tay từ sợi len tự nhiên.",
    },
    {
        "slug": "ghe-go-thu-cong",
        "name": "Ghế gỗ thủ công",
        "category_slug": "do-go",
        "price": Decimal("1250000.00"),
        "stock_quantity": 8,
        "description": "Ghế gỗ chạm khắc thủ công.",
    },
]


def _seed_categories(db) -> dict[str, int]:
    """Trả về map slug -> id (kể cả category đã tồn tại từ trước) để
    `_seed_products` resolve `category_id` đúng FK."""
    slug_to_id: dict[str, int] = {}
    for data in _CATEGORIES:
        category = db.query(Category).filter(Category.slug == data["slug"]).one_or_none()
        if category is None:
            category = Category(**data)
            db.add(category)
            db.flush()  # lấy category.id (autoincrement) ngay, CHƯA commit
            print(f"  + category mới: {data['slug']} (id={category.id})")
        else:
            print(f"  = category đã tồn tại, bỏ qua: {data['slug']} (id={category.id})")
        slug_to_id[data["slug"]] = category.id
    return slug_to_id


def _seed_products(db, category_ids: dict[str, int]) -> None:
    for data in _PRODUCTS:
        existing = db.query(Product).filter(Product.slug == data["slug"]).one_or_none()
        if existing is not None:
            print(f"  = product đã tồn tại, bỏ qua: {data['slug']} (id={existing.id})")
            continue
        product = Product(
            category_id=category_ids[data["category_slug"]],
            name=data["name"],
            slug=data["slug"],
            description=data["description"],
            price=data["price"],
            stock_quantity=data["stock_quantity"],
        )
        db.add(product)
        db.flush()
        print(f"  + product mới: {data['slug']} (id={product.id})")


def seed_dev_data() -> None:
    db = SessionLocal()
    try:
        print("Category:")
        category_ids = _seed_categories(db)
        print("Product:")
        _seed_products(db, category_ids)
        db.commit()
    finally:
        db.close()

    print("Admin:")
    seed_admin()


if __name__ == "__main__":
    seed_dev_data()
