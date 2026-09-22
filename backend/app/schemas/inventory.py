from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.base import BaseSchema

InventoryReason = Literal["restock", "damage", "audit"]


class InventoryAdjustCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(strict=True, gt=0)
    change_quantity: int = Field(strict=True, ge=-2147483647, le=2147483647)
    reason: InventoryReason
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_change(self):
        if self.change_quantity == 0:
            raise ValueError("Số lượng thay đổi phải khác 0")
        if self.reason == "restock" and self.change_quantity < 0:
            raise ValueError("Nhập kho chỉ được tăng tồn kho")
        if self.reason == "damage" and self.change_quantity > 0:
            raise ValueError("Hàng hỏng chỉ được giảm tồn kho")
        return self


class InventoryAdjustmentRead(BaseSchema):
    id: int
    product_id: int
    product_name: str
    change_quantity: int
    stock_before: int
    stock_after: int
    reason: InventoryReason
    note: str | None
    admin_id: int
    created_at: datetime


class LowStockRead(BaseSchema):
    id: int
    name: str
    stock_quantity: int
    image_url: str | None
    is_active: bool
