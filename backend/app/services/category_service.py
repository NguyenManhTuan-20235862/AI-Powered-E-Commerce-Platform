"""Business logic: Category - tách khỏi router app/routers/category.py, cùng
convention `product_service.py`/`order_service.py`.

`list_categories()` giữ NGUYÊN (task 4.2.1, Public - phục vụ filter danh mục
ở trang catalog). CRUD (create/update/delete) + các hàm validate ràng buộc
implement thêm ở đây (CRUD Category Admin).

## Category KHÔNG có cột `is_active` - xóa PHẢI là hard delete thật

Khác `Product` (soft-delete qua `is_active=False`, xem
`product_service.delete_product()`), model `Category` không có cột tương
đương - `DELETE /categories/{id}` bắt buộc `db.delete()` thật. Router PHẢI
tự validate 2 ràng buộc TRƯỚC khi gọi `delete_category()` (còn sản phẩm/còn
danh mục con) - `products.category_id`/`categories.parent_id` đều KHÔNG
khai `ondelete` (mặc định RESTRICT/NO ACTION của MySQL, quyết định có chủ
đích từ DBML ban đầu, xem app/models/category.py) - nếu không tự validate,
MySQL sẽ tự chặn bằng lỗi FK constraint khó hiểu thay vì 1 response 409 rõ
ràng.
"""

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.product_service import slugify

# Giới hạn an toàn khi đi ngược chuỗi parent_id (would_create_cycle) - chống
# lặp VÔ HẠN nếu dữ liệu categories từng bị hỏng (VD import tay tạo sẵn 1
# vòng lặp trước khi validate này tồn tại) - độ sâu thật của cây category
# trong dự án gần như luôn < 10, 100 đã rất dư dả, không cần cấu hình được.
_MAX_PARENT_CHAIN_DEPTH = 100


def list_categories(db: Session) -> list[CategoryRead]:
    """Toàn bộ danh mục - KHÔNG phân trang (số lượng danh mục nhỏ, khác hẳn
    Product), sắp theo tên cho thứ tự hiển thị ổn định giữa các lần gọi."""
    categories = db.query(Category).order_by(Category.name.asc()).all()
    return [CategoryRead.model_validate(category) for category in categories]


def generate_unique_category_slug(db: Session, base_value: str, *, exclude_category_id: int | None = None) -> str:
    """Sinh slug DUY NHẤT (`categories.slug` UNIQUE) - tái sử dụng ĐÚNG
    `product_service.slugify()` (thuật toán chuẩn hóa chuỗi thật, KHÔNG viết
    logic slug riêng). Phần kiểm tra trùng lặp PHẢI viết lại cho bảng
    `categories` (không thể tái dùng nguyên `product_service.generate_unique_slug()`
    - hàm đó query cứng bảng `products`) - nhưng giữ ĐÚNG cấu trúc vòng lặp
    thêm hậu tố số (`-2`, `-3`...) y hệt bản gốc.
    """
    base_slug = slugify(base_value)
    slug = base_slug
    suffix = 2
    while True:
        query = db.query(Category.id).filter(Category.slug == slug)
        if exclude_category_id is not None:
            query = query.filter(Category.id != exclude_category_id)
        if query.first() is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def get_category_by_id(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def category_exists(db: Session, category_id: int) -> bool:
    return db.query(Category.id).filter(Category.id == category_id).first() is not None


def count_products_in_category(db: Session, category_id: int) -> int:
    return db.query(Product).filter(Product.category_id == category_id).count()


def count_child_categories(db: Session, category_id: int) -> int:
    return db.query(Category).filter(Category.parent_id == category_id).count()


def would_create_cycle(db: Session, category_id: int, new_parent_id: int) -> bool:
    """`category_id` đang được sửa để có cha mới là `new_parent_id` - có tạo
    vòng lặp phân cấp không?

    Đi ngược chuỗi `parent_id` từ `new_parent_id` lên tới gốc - nếu gặp lại
    ĐÚNG `category_id`, nghĩa là `category_id` hiện đang là TỔ TIÊN của
    `new_parent_id` trong cây hiện tại, gán `category_id.parent_id =
    new_parent_id` sẽ khép vòng. Bắt được CẢ 2 trường hợp bằng CÙNG 1 vòng
    lặp: "cha của chính mình" (`new_parent_id == category_id`, phát hiện
    ngay bước đầu) VÀ vòng lặp GIÁN TIẾP qua nhiều cấp trung gian (VD A hiện
    là cha của B, đổi A thành con của B - hoặc chuỗi dài hơn A->B->C rồi đổi
    A thành con của C) - không giới hạn độ sâu THẬT, chỉ giới hạn bởi
    `_MAX_PARENT_CHAIN_DEPTH` để chống dữ liệu hỏng gây lặp vô hạn.
    """
    current_id: int | None = new_parent_id
    depth = 0
    while current_id is not None and depth < _MAX_PARENT_CHAIN_DEPTH:
        if current_id == category_id:
            return True
        current_id = db.query(Category.parent_id).filter(Category.id == current_id).scalar()
        depth += 1
    return False


def create_category(db: Session, payload: CategoryCreate, slug: str) -> Category:
    """`slug`: đã sinh sẵn (unique) qua `generate_unique_category_slug()` -
    router gọi trước khi vào đây, cùng convention `product_service.create_product()`."""
    category = Category(
        name=payload.name,
        slug=slug,
        description=payload.description,
        parent_id=payload.parent_id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, payload: CategoryUpdate) -> Category:
    """`category`: đã load sẵn (router chịu trách nhiệm 404 nếu không tìm
    thấy, validate `parent_id`/vòng lặp TRƯỚC khi gọi hàm này).
    `exclude_unset=True` - CHỈ áp dụng field THẬT SỰ có trong request, cùng
    pattern `product_service.update_product()`."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    """Hard delete THẬT - xem giải thích đầy đủ ở docstring module. Router
    PHẢI tự check `count_products_in_category()`/`count_child_categories()`
    (trả 409 nếu > 0) TRƯỚC KHI gọi hàm này."""
    db.delete(category)
    db.commit()
