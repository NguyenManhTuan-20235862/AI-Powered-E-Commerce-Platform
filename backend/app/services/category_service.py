"""Business logic: Category (task 4.2.1) - hiện chỉ `list_categories()`,
phục vụ `GET /categories` (public, filter danh mục ở trang catalog sản
phẩm). CRUD (POST/PUT/DELETE) vẫn 501 - chưa tới task quản lý danh mục
Admin, xem `app/schemas/category.py`.
"""

from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryRead


def list_categories(db: Session) -> list[CategoryRead]:
    """Toàn bộ danh mục - KHÔNG phân trang (số lượng danh mục nhỏ, khác hẳn
    Product), sắp theo tên cho thứ tự hiển thị ổn định giữa các lần gọi."""
    categories = db.query(Category).order_by(Category.name.asc()).all()
    return [CategoryRead.model_validate(category) for category in categories]
