"""Router: Product Module (`/products`).

Khung endpoint theo docs/API_SPEC.md - mục 3. Logic thật (query MySQL, upload
ảnh...) sẽ implement ở task 3.4.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse, MessageResponse, PaginatedData
from app.schemas.product import ProductCreate, ProductImageRead, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["Product"])


@router.get(
    "",
    response_model=APIResponse[PaginatedData[ProductRead]],
    summary="Danh sách sản phẩm",
)
def list_products() -> APIResponse[PaginatedData[ProductRead]]:
    """Danh sách sản phẩm (phân trang, filter theo category/giá, search theo tên). Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.get(
    "/{product_id}",
    response_model=APIResponse[ProductRead],
    summary="Chi tiết 1 sản phẩm",
    responses={404: {"description": "Không tìm thấy sản phẩm"}},
)
def get_product(product_id: str) -> APIResponse[ProductRead]:
    """Chi tiết 1 sản phẩm. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.get(
    "/{product_id}/related",
    response_model=APIResponse[list[ProductRead]],
    summary="Sản phẩm liên quan / tương tự",
    responses={404: {"description": "Không tìm thấy sản phẩm"}},
)
def get_related_products(product_id: str) -> APIResponse[list[ProductRead]]:
    """Sản phẩm liên quan / tương tự (dùng chung logic với AI gợi ý thay thế). Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.post(
    "",
    response_model=APIResponse[ProductRead],
    summary="Tạo sản phẩm mới",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(forbidden=True),
)
def create_product(
    payload: ProductCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[ProductRead]:
    """Tạo sản phẩm mới. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.put(
    "/{product_id}",
    response_model=APIResponse[ProductRead],
    summary="Cập nhật sản phẩm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[ProductRead]:
    """Cập nhật sản phẩm. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Xóa (hoặc ẩn) sản phẩm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def delete_product(
    product_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> MessageResponse:
    """Xóa (hoặc ẩn) sản phẩm. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")


@router.post(
    "/{product_id}/image",
    response_model=APIResponse[ProductImageRead],
    summary="Upload ảnh sản phẩm",
    responses=auth_responses(forbidden=True, not_found=True),
)
def upload_product_image(
    product_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> APIResponse[ProductImageRead]:
    """Upload ảnh sản phẩm. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 3.4")
