"""Router: Product Module (`/products`, task 3.4.1).

Khung endpoint theo docs/API_SPEC.md - mục 3.
"""

from decimal import Decimal
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.core.cache import get_or_set_cache, invalidate_by_prefix
from app.core.database import get_db, get_redis
from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.core.storage import save_product_image
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, MessageResponse, PaginatedResponse, PaginationParams, success_response
from app.schemas.product import ProductCreate, ProductImageRead, ProductRead, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products", tags=["Product"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[ProductRead]],
    summary="Danh sách sản phẩm",
)
def list_products(
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    pagination: Annotated[PaginationParams, Depends()],
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    search: str | None = None,
    sort_by: product_service.ProductSortBy | None = None,
    in_stock: bool | None = None,
) -> APIResponse[PaginatedResponse[ProductRead]]:
    """Danh sách sản phẩm (phân trang, filter category/giá/tồn kho, search
    theo tên, sắp xếp theo `sort_by` - task 4.2.1: "newest" mặc định/không
    truyền, "price_asc", "price_desc"). Public - CHỈ trả sản phẩm
    `is_active=True`.

    Cache qua Redis (`get_or_set_cache`, task 3.3.1) - key theo ĐÚNG combo
    filter/trang/sắp-xếp hiện tại (`build_product_list_cache_key`), KHÔNG
    phải 1 key tĩnh, vì mỗi combo là 1 tập dữ liệu khác nhau. Bị invalidate
    chủ động (`invalidate_by_prefix`) ngay khi Admin CRUD - xem
    `PRODUCT_LIST_CACHE_PREFIX`/`app/services/product_service.py`.
    """
    cache_key = product_service.build_product_list_cache_key(
        page=pagination.page,
        page_size=pagination.page_size,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        in_stock=in_stock,
    )
    result = get_or_set_cache(
        redis_client,
        cache_key,
        lambda: product_service.list_products(
            db,
            page=pagination.page,
            page_size=pagination.page_size,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            search=search,
            sort_by=sort_by,
            in_stock=in_stock,
        ),
        ttl_seconds=product_service.PRODUCT_LIST_CACHE_TTL_SECONDS,
        adapter=TypeAdapter(PaginatedResponse[ProductRead]),
    )
    return success_response(data=result)


@router.get(
    "/admin",
    response_model=APIResponse[PaginatedResponse[ProductRead]],
    summary="Danh sách sản phẩm (Admin - gồm cả sản phẩm đã ẩn)",
    responses=auth_responses(forbidden=True),
)
def list_products_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    category_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
) -> APIResponse[PaginatedResponse[ProductRead]]:
    """Danh sách sản phẩm cho trang quản lý (task 4.4.1) - KHÔNG lọc
    `is_active` mặc định (khác `GET /products` public), lọc được qua
    `?is_active=true/false` nếu Admin muốn xem riêng nhóm đang hiện/đã ẩn.
    Yêu cầu: Admin.

    Đăng ký TRƯỚC `GET /{id_or_slug}` (path cố định `/admin` phải đứng trước
    route templated, giống quy ước đã áp dụng cho `/orders/admin` - nếu
    không, `/{id_or_slug}` sẽ nuốt mất request `/products/admin`, hiểu nhầm
    "admin" là 1 slug/id)."""
    result = product_service.list_products_admin(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        category_id=category_id,
        search=search,
        is_active=is_active,
    )
    return success_response(data=result)


@router.get(
    "/{id_or_slug}",
    response_model=APIResponse[ProductRead],
    summary="Chi tiết 1 sản phẩm",
    responses={404: {"description": "Không tìm thấy sản phẩm"}},
)
def get_product(id_or_slug: str, db: Annotated[Session, Depends(get_db)]) -> APIResponse[ProductRead]:
    """Chi tiết 1 sản phẩm - nhận `id` (số) HOẶC `slug` (task 4.2.2, khớp URL
    trang chi tiết Frontend link theo slug - xem
    `product_service._id_or_slug_filter()`). Public - CHỈ trả sản phẩm
    `is_active=True`."""
    product_read = product_service.get_active_product_read(db, id_or_slug)
    if product_read is None:
        raise _not_found()
    return success_response(data=product_read)


@router.get(
    "/{id_or_slug}/related",
    response_model=APIResponse[list[ProductRead]],
    summary="Sản phẩm liên quan / tương tự",
    responses={404: {"description": "Không tìm thấy sản phẩm"}},
)
def get_related_products(id_or_slug: str, db: Annotated[Session, Depends(get_db)]) -> APIResponse[list[ProductRead]]:
    """Sản phẩm liên quan / tương tự - nhận `id` HOẶC `slug` (task 4.2.2, xem
    `get_product` ở trên). Cùng category, loại trừ chính nó, tối
    đa `product_service.RELATED_PRODUCTS_LIMIT` sản phẩm). Public."""
    related = product_service.list_related_products(db, id_or_slug)
    if related is None:
        raise _not_found()
    return success_response(data=related)


@router.post(
    "",
    response_model=APIResponse[ProductRead],
    summary="Tạo sản phẩm mới",
    status_code=status.HTTP_201_CREATED,
    responses={**auth_responses(forbidden=True), 400: {"description": "category_id không tồn tại"}},
)
def create_product(
    payload: ProductCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[ProductRead]:
    """Tạo sản phẩm mới. Yêu cầu: Admin."""
    category_name = product_service.get_category_name(db, payload.category_id)
    if category_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id không tồn tại")

    slug = product_service.generate_unique_slug(db, payload.slug or payload.name)
    product = product_service.create_product(db, payload, slug)

    invalidate_by_prefix(redis_client, product_service.PRODUCT_LIST_CACHE_PREFIX)
    return success_response(
        data=product_service.to_product_read(product, category_name),
        message="Tạo sản phẩm thành công",
    )


@router.put(
    "/{product_id}",
    response_model=APIResponse[ProductRead],
    summary="Cập nhật sản phẩm",
    responses={**auth_responses(forbidden=True, not_found=True), 400: {"description": "category_id không tồn tại"}},
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[ProductRead]:
    """Cập nhật sản phẩm. Yêu cầu: Admin.

    KHÔNG nhận `stock_quantity` (không có field này trong `ProductUpdate`) -
    xem giải thích rủi ro race condition ở `app/schemas/product.py`.
    """
    product = product_service.get_product_by_id(db, product_id)
    if product is None:
        raise _not_found()

    if payload.category_id is not None and product_service.get_category_name(db, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id không tồn tại")

    if payload.slug is not None:
        payload = payload.model_copy(
            update={"slug": product_service.generate_unique_slug(db, payload.slug, exclude_product_id=product_id)}
        )

    updated = product_service.update_product(db, product, payload)
    category_name = product_service.get_category_name(db, updated.category_id)
    assert category_name is not None  # vừa validate ở trên (hoặc chưa đổi category_id) - luôn tồn tại

    invalidate_by_prefix(redis_client, product_service.PRODUCT_LIST_CACHE_PREFIX)
    return success_response(
        data=product_service.to_product_read(updated, category_name),
        message="Cập nhật sản phẩm thành công",
    )


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Xóa (hoặc ẩn) sản phẩm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def delete_product(
    product_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> MessageResponse:
    """Ẩn sản phẩm (soft-delete, `is_active=False`) - KHÔNG xóa cứng, bảo
    toàn lịch sử `order_items`. Yêu cầu: Admin."""
    product = product_service.get_product_by_id(db, product_id)
    if product is None:
        raise _not_found()

    product_service.delete_product(db, product)
    invalidate_by_prefix(redis_client, product_service.PRODUCT_LIST_CACHE_PREFIX)
    return MessageResponse(message="Đã ẩn sản phẩm")


@router.post(
    "/{product_id}/image",
    response_model=APIResponse[ProductImageRead],
    summary="Upload ảnh sản phẩm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def upload_product_image(
    product_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    file: UploadFile = File(...),
) -> APIResponse[ProductImageRead]:
    """Upload ảnh sản phẩm - lưu local (xem `app/core/storage.py`), cập nhật
    `products.image_url`. Yêu cầu: Admin."""
    product = product_service.get_product_by_id(db, product_id)
    if product is None:
        raise _not_found()

    image_url = save_product_image(file, product_id)
    product.image_url = image_url
    db.commit()

    invalidate_by_prefix(redis_client, product_service.PRODUCT_LIST_CACHE_PREFIX)
    return success_response(data=ProductImageRead(image_url=image_url), message="Upload ảnh thành công")
