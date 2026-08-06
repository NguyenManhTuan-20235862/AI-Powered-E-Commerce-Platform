"""Router: Cart Module (`/cart`).

Khung endpoint theo docs/API_SPEC.md - mục 4. Toàn bộ endpoint yêu cầu Customer
(Admin bị chặn 403 - giỏ hàng không có ý nghĩa với tài khoản Admin).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartRead
from app.schemas.common import APIResponse, MessageResponse

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=APIResponse[CartRead],
    summary="Xem giỏ hàng hiện tại",
    responses=auth_responses(forbidden=True),
)
def get_cart(current_user: Annotated[User, Depends(require_role(UserRole.customer))]) -> APIResponse[CartRead]:
    """Xem giỏ hàng hiện tại. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.post(
    "/items",
    response_model=APIResponse[CartRead],
    summary="Thêm sản phẩm vào giỏ",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(forbidden=True),
)
def add_cart_item(
    payload: CartItemCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[CartRead]:
    """Thêm sản phẩm vào giỏ. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/items/{item_id}",
    response_model=APIResponse[CartRead],
    summary="Cập nhật số lượng sản phẩm trong giỏ",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_cart_item(
    item_id: str,
    payload: CartItemUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[CartRead]:
    """Cập nhật số lượng sản phẩm trong giỏ. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.delete(
    "/items/{item_id}",
    response_model=APIResponse[CartRead],
    summary="Xóa sản phẩm khỏi giỏ",
    responses=auth_responses(forbidden=True, not_found=True),
)
def remove_cart_item(
    item_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[CartRead]:
    """Xóa sản phẩm khỏi giỏ. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.delete(
    "",
    response_model=MessageResponse,
    summary="Xóa toàn bộ giỏ hàng",
    responses=auth_responses(forbidden=True),
)
def clear_cart(current_user: Annotated[User, Depends(require_role(UserRole.customer))]) -> MessageResponse:
    """Xóa toàn bộ giỏ hàng. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
