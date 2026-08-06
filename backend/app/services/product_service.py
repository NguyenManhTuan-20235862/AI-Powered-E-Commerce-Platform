"""Business logic: Product (task 3.4.1) - tách khỏi router app/routers/product.py.

Router chịu trách nhiệm validate tồn tại (category_id hợp lệ? sản phẩm có
tồn tại?) và raise HTTPException - đúng convention đã dùng ở
`app/services/auth_service.py` (router gọi `get_user_by_email` trước, tự
raise 400 nếu trùng, RỒI mới gọi `register_user`) - service ở đây chỉ thao
tác DB, không tự raise HTTP error.
"""

import re
import unicodedata
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.schemas.common import PaginatedResponse, paginated_response
from app.schemas.product import CategorySummary, ProductCreate, ProductRead, ProductUpdate

RELATED_PRODUCTS_LIMIT = 8

# 5 phút - cân bằng giữa "dữ liệu đủ mới" và "giảm tải MySQL thật sự đáng
# kể" (xem phân tích đầy đủ ở tests/test_cache.py, task 3.3.1 -
# RECOMMENDED_HOT_PRODUCTS_TTL_SECONDS). Giờ dùng THẬT cho GET /products.
PRODUCT_LIST_CACHE_TTL_SECONDS = 300
# Tiền tố CHUNG cho mọi biến thể key (filter/trang khác nhau) - dùng với
# app.core.cache.invalidate_by_prefix() để xóa SẠCH toàn bộ biến thể 1 lượt
# sau CRUD (task 3.4.1 - đã xác nhận lại với người dùng, đổi từ TTL-only ở
# task 3.3.1 sang invalidate chủ động vì giờ có CRUD thật).
PRODUCT_LIST_CACHE_PREFIX = "products:list:"


def slugify(value: str) -> str:
    """Chuẩn hóa 1 chuỗi (tên sản phẩm, hoặc slug người dùng tự nhập) thành
    URL-safe slug: bỏ dấu tiếng Việt (NFD decompose + loại combining mark),
    chữ thường, khoảng trắng/ký tự đặc biệt -> dấu gạch ngang, gộp nhiều dấu
    gạch ngang liên tiếp, bỏ dấu gạch ngang ở đầu/cuối.

    Áp dụng cho CẢ 2 trường hợp - slug tự sinh từ `name` LẪN slug người dùng
    tự nhập tay (`ProductCreate.slug`/`ProductUpdate.slug`) - đảm bảo slug
    LUÔN URL-safe bất kể nguồn nhập, không cần validate riêng bằng regex.
    """
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    # "đ"/"Đ" không bị NFD tách thành base-letter + combining mark (khác các
    # ký tự có dấu khác) - phải thay tay riêng.
    without_accents = without_accents.replace("đ", "d").replace("Đ", "D")
    slug = re.sub(r"[^a-z0-9]+", "-", without_accents.lower()).strip("-")
    return slug or "san-pham"


def generate_unique_slug(db: Session, base_value: str, *, exclude_product_id: int | None = None) -> str:
    """Sinh slug DUY NHẤT (`products.slug` UNIQUE) - nếu slug cơ bản đã tồn
    tại (VD 2 sản phẩm cùng tên), thêm hậu tố số (`-2`, `-3`...) tới khi
    không trùng. `exclude_product_id`: dùng lúc UPDATE - không tính chính
    sản phẩm đang sửa là "trùng" với slug hiện tại của nó.
    """
    base_slug = slugify(base_value)
    slug = base_slug
    suffix = 2
    while True:
        query = db.query(Product.id).filter(Product.slug == slug)
        if exclude_product_id is not None:
            query = query.filter(Product.id != exclude_product_id)
        if query.first() is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def build_product_list_cache_key(
    *,
    page: int,
    page_size: int,
    category_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    search: str | None,
) -> str:
    """Cache key cho ĐÚNG 1 combo filter/trang cụ thể (KHÔNG phải 1 key
    tĩnh) - mỗi combo là 1 tập dữ liệu khác nhau, cần cache riêng."""
    parts = [
        f"page:{page}",
        f"page_size:{page_size}",
        f"category:{category_id if category_id is not None else 'all'}",
        f"min_price:{min_price if min_price is not None else '-'}",
        f"max_price:{max_price if max_price is not None else '-'}",
        f"search:{search or '-'}",
    ]
    return PRODUCT_LIST_CACHE_PREFIX + ":".join(parts)


def to_product_read(product: Product, category_name: str) -> ProductRead:
    return ProductRead(
        id=product.id,
        category=CategorySummary(id=product.category_id, name=category_name),
        name=product.name,
        slug=product.slug,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        image_url=product.image_url,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def get_category_name(db: Session, category_id: int) -> str | None:
    """None nếu category_id không tồn tại - router tự raise 400 (validate
    input trước khi tạo/sửa sản phẩm)."""
    return db.query(Category.name).filter(Category.id == category_id).scalar()


def get_product_by_id(db: Session, product_id: int) -> Product | None:
    """Lấy sản phẩm theo ID - BẤT KỂ `is_active` (dùng cho Admin: PUT/DELETE/
    upload ảnh cũng phải thao tác được trên sản phẩm ĐÃ ẩn, VD để kích hoạt
    lại qua `PUT .../is_active=true`). KHÁC hẳn các hàm dành cho endpoint
    Public bên dưới (list/detail/related) - LUÔN lọc `is_active=True`.
    """
    return db.get(Product, product_id)


def list_products(
    db: Session,
    *,
    page: int,
    page_size: int,
    category_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    search: str | None,
) -> PaginatedResponse[ProductRead]:
    """Danh sách sản phẩm CÔNG KHAI - CHỈ `is_active=True` (ẩn sản phẩm đã
    xóa mềm). JOIN thẳng `categories` (KHÔNG dùng SQLAlchemy `relationship()`
    - model `Product` cố tình không khai báo quan hệ ORM, xem
    `app/models/product.py`) để lấy `category.name` trong CÙNG 1 query,
    tránh N+1 (1 query duy nhất cho cả trang, không phải 1 query/sản phẩm).
    """
    query = (
        db.query(Product, Category.name)
        .join(Category, Product.category_id == Category.id)
        .filter(Product.is_active.is_(True))
    )
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    total = query.count()
    rows = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [to_product_read(product, category_name) for product, category_name in rows]
    return paginated_response(items, total, page, page_size)


def get_active_product_read(db: Session, product_id: int) -> ProductRead | None:
    """Chi tiết 1 sản phẩm CÔNG KHAI - None nếu không tồn tại HOẶC đã bị ẩn
    (`is_active=False`) - router trả 404 như nhau cho cả 2 trường hợp, không
    phân biệt "không tồn tại" với "đã ẩn" ra ngoài (tương tự nguyên tắc 1
    message lỗi duy nhất ở `app/core/security.py:_unauthorized`)."""
    row = (
        db.query(Product, Category.name)
        .join(Category, Product.category_id == Category.id)
        .filter(Product.id == product_id, Product.is_active.is_(True))
        .first()
    )
    if row is None:
        return None
    product, category_name = row
    return to_product_read(product, category_name)


def list_related_products(db: Session, product_id: int) -> list[ProductRead] | None:
    """None nếu sản phẩm gốc không tồn tại/đã bị ẩn (router trả 404). Ngược
    lại, trả tối đa `RELATED_PRODUCTS_LIMIT` sản phẩm CÙNG category, loại
    trừ chính nó, cũng CHỈ `is_active=True`."""
    anchor = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if anchor is None:
        return None

    rows = (
        db.query(Product, Category.name)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.category_id == anchor.category_id,
            Product.id != product_id,
            Product.is_active.is_(True),
        )
        .order_by(Product.id.desc())
        .limit(RELATED_PRODUCTS_LIMIT)
        .all()
    )
    return [to_product_read(product, category_name) for product, category_name in rows]


def create_product(db: Session, payload: ProductCreate, slug: str) -> Product:
    """`slug`: đã sinh sẵn (unique) qua `generate_unique_slug` - router gọi
    trước khi vào đây (giữ nhất quán với việc router chịu trách nhiệm mọi
    bước validate/chuẩn bị dữ liệu trước khi service ghi DB)."""
    product = Product(
        category_id=payload.category_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        image_url=payload.image_url,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    """`product`: đã load sẵn (router chịu trách nhiệm 404 nếu không tìm
    thấy). `exclude_unset=True` - CHỈ áp dụng field THẬT SỰ có trong request
    (phân biệt "không truyền field" với "truyền field = null" cho field
    nullable như `description`/`image_url`) - đúng ngữ nghĩa partial update,
    field không truyền giữ nguyên giá trị cũ.

    KHÔNG có `stock_quantity` trong `ProductUpdate` - xem giải thích đầy đủ ở
    `app/schemas/product.py`.
    """
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Soft-delete (`is_active=False`) - KHÔNG xóa cứng, đúng nguyên tắc đã
    thiết kế (`ON DELETE RESTRICT` từ `order_items`/`cart_items` tới
    `products`, xem `docs/DATABASE_SCHEMA.md`) - `order_items.product_id`
    vẫn phải tham chiếu được sản phẩm cũ cho lịch sử hóa đơn dù không còn
    bán. Idempotent - gọi lại trên sản phẩm ĐÃ ẩn không lỗi, chỉ set lại
    cùng giá trị.
    """
    product.is_active = False
    db.commit()
