"""Router: Review Module (`/reviews`) — MongoDB.

`GET /products/{product_id}/reviews` và `POST /products/{product_id}/reviews`
nằm dưới `/products/{product_id}/reviews`, `DELETE /reviews/{review_id}` và
`GET /reviews` (Admin, mới thêm - task "Hoàn thiện review sản phẩm", KHÔNG có
trong docs/API_SPEC.md bản gốc) nằm dưới `/reviews` - router này KHÔNG dùng
prefix chung mà khai báo full path riêng cho từng endpoint.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database as MongoDatabase
from sqlalchemy.orm import Session

from app.core.database import get_db, get_mongo_db
from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.common import (
    APIResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    paginated_response,
    success_response,
)
from app.schemas.review import ReviewAdminRead, ReviewCreateRequest, ReviewListRead, ReviewRead
from app.services import product_service, review_service

router = APIRouter(tags=["Review"])


def _product_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")


@router.get(
    "/products/{product_id}/reviews",
    response_model=APIResponse[ReviewListRead],
    # response_model_by_alias=False - ReviewRead.id khai `Field(alias="_id")`
    # (validate từ document Mongo thật, key "_id") nhưng KHÔNG được lộ "_id"
    # ra JSON response công khai (mặc định FastAPI serialize theo alias,
    # response_model_by_alias=True) - mọi resource khác trong API đều trả
    # "id" (UserResponse/ProductRead/OrderRead...), review cũng phải nhất
    # quán, không rò rỉ quy ước nội bộ của MongoDB ra hợp đồng API công khai.
    response_model_by_alias=False,
    summary="Danh sách review của 1 sản phẩm",
    responses={404: {"description": "Không tìm thấy sản phẩm"}},
)
def list_product_reviews(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    mongo_db: Annotated[MongoDatabase, Depends(get_mongo_db)],
    pagination: Annotated[PaginationParams, Depends()],
) -> APIResponse[ReviewListRead]:
    """Danh sách review của 1 sản phẩm, kèm điểm trung bình + tổng số review.
    Public - 404 nếu sản phẩm không tồn tại/đã ẩn (cùng quy tắc `GET
    /products/{id_or_slug}`)."""
    if product_service.get_active_product_read(db, str(product_id)) is None:
        raise _product_not_found()

    items, total, average_rating = review_service.list_product_reviews(
        mongo_db, product_id=product_id, page=pagination.page, page_size=pagination.page_size
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size if pagination.page_size > 0 else 0
    return success_response(
        data=ReviewListRead(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            average_rating=average_rating,
        )
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=APIResponse[ReviewRead],
    response_model_by_alias=False,  # xem giải thích ở GET /products/{id}/reviews phía trên
    summary="Viết review sản phẩm",
    status_code=status.HTTP_201_CREATED,
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "Chưa mua sản phẩm này / đơn hàng chưa giao / sai đơn hàng"},
        409: {"description": "Đã đánh giá sản phẩm này từ đúng đơn hàng đó rồi"},
    },
)
def create_product_review(
    product_id: int,
    payload: ReviewCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
    mongo_db: Annotated[MongoDatabase, Depends(get_mongo_db)],
) -> APIResponse[ReviewRead]:
    """Viết review - CHỈ khi đã mua ĐÚNG sản phẩm này qua ĐÚNG `order_id` đã
    `delivered` (`review_service.verify_purchase()`). Yêu cầu: Customer."""
    if product_service.get_active_product_read(db, str(product_id)) is None:
        raise _product_not_found()

    try:
        review_service.verify_purchase(db, user_id=current_user.id, order_id=payload.order_id, product_id=product_id)
    except review_service.ReviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        review = review_service.create_review(
            mongo_db,
            product_id=product_id,
            user_id=current_user.id,
            user_name=current_user.full_name,
            order_id=payload.order_id,
            rating=payload.rating,
            comment=payload.comment,
            images=payload.images,
        )
    except review_service.DuplicateReviewError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return success_response(data=review, message="Đánh giá thành công")


@router.get(
    "/reviews",
    response_model=APIResponse[PaginatedResponse[ReviewAdminRead]],
    response_model_by_alias=False,  # xem giải thích ở GET /products/{id}/reviews phía trên
    summary="Danh sách toàn bộ review (Admin, moderation)",
    responses=auth_responses(forbidden=True),
)
def list_reviews_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    mongo_db: Annotated[MongoDatabase, Depends(get_mongo_db)],
    pagination: Annotated[PaginationParams, Depends()],
    product_id: int | None = None,
    is_deleted: bool | None = None,
) -> APIResponse[PaginatedResponse[ReviewAdminRead]]:
    """Danh sách TOÀN BỘ review phục vụ trang moderation Admin (task mở rộng,
    KHÔNG có trong docs/API_SPEC.md bản gốc) - lọc được theo sản phẩm/trạng
    thái xóa mềm, mặc định trả CẢ review còn hiện lẫn đã xóa (xem
    `review_service.list_reviews_admin()`). Yêu cầu: Admin.

    Đăng ký TRƯỚC `DELETE /reviews/{review_id}` không xung đột (khác method +
    khác path templated hoàn toàn, không cần lo thứ tự như `/orders/admin`)."""
    items, total = review_service.list_reviews_admin(
        mongo_db,
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        product_id=product_id,
        is_deleted=is_deleted,
    )
    return success_response(data=paginated_response(items, total, pagination.page, pagination.page_size))


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Xóa review vi phạm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def delete_review(
    review_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    mongo_db: Annotated[MongoDatabase, Depends(get_mongo_db)],
) -> MessageResponse:
    """Xóa MỀM review vi phạm (`is_deleted=True`, giữ lại phục vụ audit
    trail/undo - xem docstring `app/schemas/review.py`). Yêu cầu: Admin. 404
    nếu `review_id` sai định dạng, không tồn tại, hoặc đã bị xóa từ trước."""
    if not review_service.soft_delete_review(mongo_db, review_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy review")
    return MessageResponse(message="Đã xóa review")
