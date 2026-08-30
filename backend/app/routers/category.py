"""Router: Category Module (`/categories`).

Khung endpoint theo docs/API_SPEC.md - mục 3.1.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import APIResponse, MessageResponse, success_response
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["Category"])


@router.get(
    "",
    response_model=APIResponse[list[CategoryRead]],
    summary="Danh sách danh mục sản phẩm",
)
def list_categories(db: Annotated[Session, Depends(get_db)]) -> APIResponse[list[CategoryRead]]:
    """Danh sách danh mục sản phẩm (task 4.2.1). Public."""
    return success_response(data=category_service.list_categories(db))


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục")


@router.post(
    "",
    response_model=APIResponse[CategoryRead],
    summary="Tạo danh mục mới",
    status_code=status.HTTP_201_CREATED,
    responses={**auth_responses(forbidden=True), 400: {"description": "parent_id không tồn tại"}},
)
def create_category(
    payload: CategoryCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CategoryRead]:
    """Tạo danh mục mới. Yêu cầu: Admin."""
    if payload.parent_id is not None and not category_service.category_exists(db, payload.parent_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent_id không tồn tại")

    slug = category_service.generate_unique_category_slug(db, payload.slug or payload.name)
    category = category_service.create_category(db, payload, slug)
    return success_response(data=CategoryRead.model_validate(category), message="Tạo danh mục thành công")


@router.put(
    "/{category_id}",
    response_model=APIResponse[CategoryRead],
    summary="Cập nhật danh mục",
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "parent_id không tồn tại, hoặc sẽ tạo vòng lặp phân cấp"},
    },
)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CategoryRead]:
    """Cập nhật danh mục. Yêu cầu: Admin."""
    category = category_service.get_category_by_id(db, category_id)
    if category is None:
        raise _not_found()

    if payload.parent_id is not None:
        if not category_service.category_exists(db, payload.parent_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent_id không tồn tại")
        if category_service.would_create_cycle(db, category_id, payload.parent_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt danh mục cha này - sẽ tạo vòng lặp phân cấp",
            )

    if payload.slug is not None:
        payload = payload.model_copy(
            update={
                "slug": category_service.generate_unique_category_slug(
                    db, payload.slug, exclude_category_id=category_id
                )
            }
        )

    updated = category_service.update_category(db, category, payload)
    return success_response(data=CategoryRead.model_validate(updated), message="Cập nhật danh mục thành công")


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="Xóa danh mục",
    responses={
        **auth_responses(forbidden=True, not_found=True),
        409: {"description": "Còn sản phẩm hoặc danh mục con thuộc về danh mục này"},
    },
)
def delete_category(
    category_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Xóa danh mục. Yêu cầu: Admin."""
    category = category_service.get_category_by_id(db, category_id)
    if category is None:
        raise _not_found()

    product_count = category_service.count_products_in_category(db, category_id)
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa danh mục còn {product_count} sản phẩm",
        )

    child_count = category_service.count_child_categories(db, category_id)
    if child_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa danh mục còn {child_count} danh mục con",
        )

    category_service.delete_category(db, category)
    return MessageResponse(message="Đã xóa danh mục")
