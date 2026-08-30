"""Router: Dashboard / Statistics Module (`/admin/dashboard`, task 5.3.1).

Endpoint theo docs/API_SPEC.md - mục 10. Cache qua Redis (`get_or_set_cache`,
TTL 5 phút) - cùng convention `app/routers/product.py` (task 3.4.1), KHÔNG
active-invalidate khi đơn hàng đổi trạng thái (xem lý do đầy đủ ở docstring
module `app/services/dashboard_service.py`).
"""

from datetime import date
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Query
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.core.cache import get_or_set_cache
from app.core.database import get_db, get_redis
from app.core.openapi_responses import auth_responses
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, success_response
from app.schemas.dashboard import DashboardSummaryRead, RevenueInterval, RevenuePointRead, TopProductRead, TopProductSortBy
from app.services import dashboard_service

router = APIRouter(prefix="/admin/dashboard", tags=["Dashboard Admin"])


@router.get(
    "/summary",
    response_model=APIResponse[DashboardSummaryRead],
    summary="Tổng quan: tổng doanh thu, số đơn hàng, số user mới",
    responses=auth_responses(forbidden=True),
)
def get_summary(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    date_from: date | None = None,
    date_to: date | None = None,
) -> APIResponse[DashboardSummaryRead]:
    """Tổng quan: tổng doanh thu (loại trừ đơn "cancelled"), tổng số đơn hàng
    (MỌI trạng thái, kể cả "cancelled" - chỉ số hoạt động, khác doanh thu),
    số user mới (role Customer). Mặc định 30 ngày gần nhất nếu không truyền
    `date_from`/`date_to`. Yêu cầu: Admin.
    """
    resolved_from, resolved_to = dashboard_service.resolve_date_range(date_from, date_to)
    result = get_or_set_cache(
        redis_client,
        dashboard_service.build_summary_cache_key(resolved_from, resolved_to),
        lambda: dashboard_service.get_summary(db, resolved_from, resolved_to),
        ttl_seconds=dashboard_service.DASHBOARD_CACHE_TTL_SECONDS,
        adapter=TypeAdapter(DashboardSummaryRead),
    )
    return success_response(data=result)


@router.get(
    "/revenue",
    response_model=APIResponse[list[RevenuePointRead]],
    summary="Doanh thu theo ngày/tuần/tháng",
    responses=auth_responses(forbidden=True),
)
def get_revenue(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    date_from: date | None = None,
    date_to: date | None = None,
    interval: RevenueInterval = "day",
) -> APIResponse[list[RevenuePointRead]]:
    """Doanh thu theo ngày/tuần/tháng (dữ liệu cho chart) - loại trừ đơn
    "cancelled". Mảng trả về LIÊN TỤC (điền 0 cho khoảng không phát sinh đơn,
    không bỏ trống) - phù hợp vẽ line/bar chart. Mặc định 30 ngày gần nhất.
    Yêu cầu: Admin.
    """
    resolved_from, resolved_to = dashboard_service.resolve_date_range(date_from, date_to)
    result = get_or_set_cache(
        redis_client,
        dashboard_service.build_revenue_cache_key(resolved_from, resolved_to, interval),
        lambda: dashboard_service.get_revenue(db, resolved_from, resolved_to, interval),
        ttl_seconds=dashboard_service.DASHBOARD_CACHE_TTL_SECONDS,
        adapter=TypeAdapter(list[RevenuePointRead]),
    )
    return success_response(data=result)


@router.get(
    "/top-products",
    response_model=APIResponse[list[TopProductRead]],
    summary="Top sản phẩm bán chạy",
    responses=auth_responses(forbidden=True),
)
def get_top_products(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    sort_by: TopProductSortBy = "quantity",
) -> APIResponse[list[TopProductRead]]:
    """Top sản phẩm bán chạy - mặc định sắp theo SỐ LƯỢNG bán
    (`sort_by=quantity`), có thể đổi sang doanh thu (`sort_by=revenue`) -
    loại trừ đơn "cancelled". Mặc định 30 ngày gần nhất, top 10. Yêu cầu: Admin.
    """
    resolved_from, resolved_to = dashboard_service.resolve_date_range(date_from, date_to)
    result = get_or_set_cache(
        redis_client,
        dashboard_service.build_top_products_cache_key(resolved_from, resolved_to, limit, sort_by),
        lambda: dashboard_service.get_top_products(db, resolved_from, resolved_to, limit=limit, sort_by=sort_by),
        ttl_seconds=dashboard_service.DASHBOARD_CACHE_TTL_SECONDS,
        adapter=TypeAdapter(list[TopProductRead]),
    )
    return success_response(data=result)
