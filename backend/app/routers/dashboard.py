"""Router: Dashboard / Statistics Module (`/admin/dashboard`).

Khung endpoint theo docs/API_SPEC.md - mục 10. Logic thống kê thật sẽ implement
ở task sau khi có dữ liệu Order/Product thật.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardSummaryRead, RevenuePointRead, TopProductRead

router = APIRouter(prefix="/admin/dashboard", tags=["Dashboard Admin"])


@router.get(
    "/summary",
    response_model=APIResponse[DashboardSummaryRead],
    summary="Tổng quan: tổng doanh thu, số đơn hàng, số user mới",
    responses=auth_responses(forbidden=True),
)
def get_summary(current_user: Annotated[dict, Depends(get_current_user)]) -> APIResponse[DashboardSummaryRead]:
    """Tổng quan: tổng doanh thu, số đơn hàng, số user mới. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/revenue",
    response_model=APIResponse[list[RevenuePointRead]],
    summary="Doanh thu theo ngày/tuần/tháng",
    responses=auth_responses(forbidden=True),
)
def get_revenue(current_user: Annotated[dict, Depends(get_current_user)]) -> APIResponse[list[RevenuePointRead]]:
    """Doanh thu theo ngày/tuần/tháng (dữ liệu cho chart). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/top-products",
    response_model=APIResponse[list[TopProductRead]],
    summary="Top sản phẩm bán chạy",
    responses=auth_responses(forbidden=True),
)
def get_top_products(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[list[TopProductRead]]:
    """Top sản phẩm bán chạy. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
