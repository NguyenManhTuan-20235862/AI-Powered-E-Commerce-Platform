"""Router: Cart Module (`/cart`, task 3.4.2).

Khung endpoint theo docs/API_SPEC.md - mục 4. Toàn bộ endpoint yêu cầu Customer
(Admin bị chặn 403 - giỏ hàng không có ý nghĩa với tài khoản Admin).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartRead
from app.schemas.common import APIResponse, MessageResponse, success_response
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=APIResponse[CartRead],
    summary="Xem giỏ hàng hiện tại",
    responses=auth_responses(forbidden=True),
)
def get_cart(
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CartRead]:
    """Xem giỏ hàng hiện tại. Yêu cầu: Customer."""
    return success_response(data=cart_service.get_cart(db, current_user.id))


@router.post(
    "/items",
    response_model=APIResponse[CartRead],
    summary="Thêm sản phẩm vào giỏ",
    status_code=status.HTTP_201_CREATED,
    responses={
        **auth_responses(forbidden=True),
        400: {"description": "Sản phẩm không tồn tại/ngừng bán/không đủ tồn kho"},
    },
)
def add_cart_item(
    payload: CartItemCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CartRead]:
    """Thêm sản phẩm vào giỏ - cộng dồn quantity nếu sản phẩm đã có trong giỏ.
    Yêu cầu: Customer."""
    try:
        cart_service.add_item(db, current_user.id, payload.product_id, payload.quantity)
    except cart_service.CartError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return success_response(data=cart_service.get_cart(db, current_user.id), message="Đã thêm vào giỏ hàng")


@router.put(
    "/items/{item_id}",
    response_model=APIResponse[CartRead],
    summary="Cập nhật số lượng sản phẩm trong giỏ",
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "Vượt quá tồn kho hoặc sản phẩm ngừng bán"},
    },
)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CartRead]:
    """Cập nhật số lượng sản phẩm trong giỏ. Yêu cầu: Customer."""
    item = cart_service.get_own_cart_item(db, current_user.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm trong giỏ")

    try:
        cart_service.update_item_quantity(db, item, payload.quantity)
    except cart_service.CartError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return success_response(data=cart_service.get_cart(db, current_user.id))


@router.delete(
    "/items/{item_id}",
    response_model=APIResponse[CartRead],
    summary="Xóa sản phẩm khỏi giỏ",
    responses=auth_responses(forbidden=True, not_found=True),
)
def remove_cart_item(
    item_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[CartRead]:
    """Xóa sản phẩm khỏi giỏ. Yêu cầu: Customer."""
    item = cart_service.get_own_cart_item(db, current_user.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm trong giỏ")

    cart_service.remove_item(db, item)
    return success_response(data=cart_service.get_cart(db, current_user.id), message="Đã xóa khỏi giỏ hàng")


@router.delete(
    "",
    response_model=MessageResponse,
    summary="Xóa toàn bộ giỏ hàng",
    responses=auth_responses(forbidden=True),
)
def clear_cart(
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Xóa toàn bộ giỏ hàng. Yêu cầu: Customer."""
    cart_service.clear_cart(db, current_user.id)
    return MessageResponse(message="Đã xóa toàn bộ giỏ hàng")
