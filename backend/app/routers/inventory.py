from datetime import date
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.cache import invalidate_by_prefix
from app.core.database import get_db, get_redis
from app.core.security import require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams, success_response
from app.schemas.inventory import InventoryAdjustCreate, InventoryAdjustmentRead, InventoryReason, LowStockRead
from app.services import inventory_service

router = APIRouter(prefix="/admin/inventory", tags=["Inventory Admin"])
Admin = Annotated[User, Depends(require_role(UserRole.admin))]
DB = Annotated[Session, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]


@router.post("/adjust", response_model=APIResponse[InventoryAdjustmentRead])
def adjust(payload: InventoryAdjustCreate, current_user: Admin, db: DB,
           redis_client: Annotated[redis.Redis, Depends(get_redis)],
           idempotency_key: Annotated[str, Header(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]):
    result = inventory_service.adjust_stock(db, current_user.id, idempotency_key, payload)
    invalidate_by_prefix(redis_client, "products:list:")
    return success_response(result, "Đã điều chỉnh tồn kho")


@router.get("/adjustments", response_model=APIResponse[PaginatedResponse[InventoryAdjustmentRead]])
def adjustments(current_user: Admin, db: DB, pagination: Pagination,
                product_id: Annotated[int | None, Query(gt=0)] = None,
                reason: InventoryReason | None = None, date_from: date | None = None, date_to: date | None = None):
    return success_response(inventory_service.list_adjustments(db, pagination.page, pagination.page_size, product_id, reason, date_from, date_to))


@router.get("/low-stock", response_model=APIResponse[PaginatedResponse[LowStockRead]])
def low_stock(current_user: Admin, db: DB, pagination: Pagination,
              threshold: Annotated[int, Query(gt=0, le=2147483647)] = 10,
              is_active: bool | None = True):
    return success_response(inventory_service.low_stock(db, pagination.page, pagination.page_size, threshold, is_active))
