"""Pydantic schemas: Dashboard / Statistics (task 5.3.1) - viết lại HOÀN
TOÀN từ placeholder cũ (KHÔNG vá), cùng nguyên tắc đã áp dụng cho
`ProductRead` ở task 3.4.1 (xem docs/KNOWN_TODOS.md #14): `TopProductRead`
cũ khai `product_id: str` trong khi `products.id` là `BigInteger` - sai kiểu
từ gốc, không có gì để giữ lại.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

RevenueInterval = Literal["day", "week", "month"]
TopProductSortBy = Literal["quantity", "revenue"]


class DashboardSummaryRead(BaseModel):
    """`date_from`/`date_to` trả kèm trong response - Frontend cần biết CHÍNH
    XÁC khoảng thời gian đã áp dụng khi không truyền query param (mặc định 30
    ngày gần nhất, xem `dashboard_service.resolve_date_range()`), tránh hiểu
    lầm "3 số liệu này tính từ khi nào"."""

    date_from: date
    date_to: date
    total_revenue: Decimal
    total_orders: int
    new_users: int


class RevenuePointRead(BaseModel):
    # Nhãn khoảng thời gian - định dạng phụ thuộc `interval` lúc gọi API:
    # "day" -> "2026-08-30", "week" -> "2026-W35" (ISO week), "month" ->
    # "2026-08". Kiểu `str` chung cho cả 3 (không tách 3 field ngày/tuần/
    # tháng riêng) - Chart.js chỉ cần 1 trục nhãn dạng chuỗi để vẽ, không cần
    # phân biệt kiểu ở tầng response.
    period: str
    revenue: Decimal


class TopProductRead(BaseModel):
    product_id: int
    name: str
    quantity_sold: int
    revenue: Decimal
