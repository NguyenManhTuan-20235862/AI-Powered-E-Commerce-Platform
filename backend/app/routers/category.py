"""Router: Category Module (`/categories`).

Khung endpoint theo docs/API_SPEC.md - mục 3.1.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import APIResponse, MessageResponse

router = APIRouter(prefix="/categories", tags=["Category"])


@router.get(
    "",
    response_model=APIResponse[list[CategoryRead]],
    summary="Danh sách danh mục sản phẩm",
)
def list_categories() -> APIResponse[list[CategoryRead]]:
    """Danh sách danh mục sản phẩm. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.post(
    "",
    response_model=APIResponse[CategoryRead],
    summary="Tạo danh mục mới",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(forbidden=True),
)
def create_category(
    payload: CategoryCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[CategoryRead]:
    """Tạo danh mục mới. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/{category_id}",
    response_model=APIResponse[CategoryRead],
    summary="Cập nhật danh mục",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_category(
    category_id: str,
    payload: CategoryUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[CategoryRead]:
    """Cập nhật danh mục. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="Xóa danh mục",
    responses=auth_responses(forbidden=True, not_found=True),
)
def delete_category(
    category_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> MessageResponse:
    """Xóa danh mục. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
