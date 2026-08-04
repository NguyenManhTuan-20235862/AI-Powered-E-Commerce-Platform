"""Pydantic schemas: Dashboard / Statistics (response models cho Admin).

TODO (Thành viên A): hoàn thiện field thật khi implement thống kê.
"""

from pydantic import BaseModel


class DashboardSummaryRead(BaseModel):
    total_revenue: float
    total_orders: int
    new_users: int


class RevenuePointRead(BaseModel):
    date: str
    revenue: float


class TopProductRead(BaseModel):
    product_id: str
    name: str
    quantity_sold: int
