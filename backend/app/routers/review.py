"""Router: Review Module (`/reviews`) — MongoDB.

Khung endpoint theo docs/API_SPEC.md - mục 7. Lưu ý: 2 endpoint đầu nằm dưới
`/products/{product_id}/reviews`, không phải dưới `/reviews` - do đó router này
KHÔNG dùng prefix chung mà khai báo full path riêng cho từng endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, MessageResponse, PaginatedResponse
from app.schemas.review import ReviewCreate, ReviewRead

router = APIRouter(tags=["Review"])


@router.get(
    "/products/{product_id}/reviews",
    response_model=APIResponse[PaginatedResponse[ReviewRead]],
    summary="Danh sách review của 1 sản phẩm",
)
def list_product_reviews(product_id: str) -> APIResponse[PaginatedResponse[ReviewRead]]:
    """Danh sách review của 1 sản phẩm. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.post(
    "/products/{product_id}/reviews",
    response_model=APIResponse[ReviewRead],
    summary="Viết review sản phẩm",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(forbidden=True, not_found=True),
)
def create_product_review(
    product_id: str,
    payload: ReviewCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[ReviewRead]:
    """Viết review (chỉ khi đã mua sản phẩm). Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Xóa review vi phạm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def delete_review(
    review_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> MessageResponse:
    """Xóa review vi phạm. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
