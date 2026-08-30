"""Business logic: Dashboard / Statistics (task 5.3.1) - tách khỏi router
`app/routers/dashboard.py`, cùng convention `product_service.py`/`order_service.py`.

## Đơn nào tính vào "doanh thu" (`total_revenue`, `revenue`)

Loại trừ CHỈ trạng thái `cancelled` (tính `pending`+`confirmed`+`shipping`+
`delivered`) - đã xác nhận với người dùng trước khi code. `cancelled` là
trạng thái DUY NHẤT giao dịch bị hủy thật (đã hoàn kho qua
`order_service._restock_order_items`, không tiền nào đổi tay) - mọi trạng
thái khác đại diện 1 đơn đã đặt thành công.

## `total_orders` (summary) đếm CẢ đơn "cancelled" - KHÁC `total_revenue`

Quyết định riêng (không nằm trong 8 điểm đã xác nhận, nêu rõ ở đây để không
âm thầm quyết định): "tổng đơn hàng" là chỉ số SỐ LƯỢNG hoạt động đặt hàng
trong kỳ (bao gồm cả đơn bị hủy - tự nó là thông tin hữu ích, VD tỷ lệ hủy
cao), khác hẳn "doanh thu" (chỉ tính đơn thành công). Tách riêng 2 bộ lọc
(`REVENUE_ELIGIBLE_STATUSES` chỉ áp dụng cho revenue) thay vì dùng chung 1
filter cho cả 2 chỉ số.

## Cache

TTL 300s (5 phút, đã xác nhận) - dùng `get_or_set_cache`/`invalidate_by_prefix`
có sẵn (`app/core/cache.py`, task 3.3.1). KHÔNG active-invalidate khi đơn
hàng đổi trạng thái (khác `product_service.py` cho CRUD sản phẩm) - dữ liệu
thống kê đã xác nhận không cần tức thời (task 5.3.1, quyết định 1: dashboard
chỉ fetch khi Admin mở trang/bấm refresh, không cần đẩy realtime), TTL-only
là đủ.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardSummaryRead, RevenueInterval, RevenuePointRead, TopProductRead, TopProductSortBy

REVENUE_ELIGIBLE_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.pending, OrderStatus.confirmed, OrderStatus.shipping, OrderStatus.delivered}
)

# 30 ngày gần nhất - áp dụng khi không truyền date_from/date_to (đã xác nhận).
DEFAULT_LOOKBACK_DAYS = 30

DASHBOARD_CACHE_PREFIX = "dashboard:"
DASHBOARD_CACHE_TTL_SECONDS = 300


def resolve_date_range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    """`date_to` mặc định hôm nay, `date_from` mặc định `DEFAULT_LOOKBACK_DAYS`
    ngày TRƯỚC `date_to` (không phải trước hôm nay - nếu Admin CHỈ truyền
    `date_to` trong quá khứ, khoảng 30 ngày phải tính lùi từ mốc đó, không
    phải từ hôm nay)."""
    resolved_to = date_to if date_to is not None else date.today()
    resolved_from = date_from if date_from is not None else resolved_to - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)
    return resolved_from, resolved_to


def _end_exclusive(date_to: date):
    """`created_at < date_to + 1 ngày` - để NGÀY `date_to` được tính TRỌN VẸN
    (cùng nguyên tắc `order_service.list_orders`)."""
    return date_to + timedelta(days=1)


def _period_label(day: date, interval: RevenueInterval) -> str:
    if interval == "day":
        return day.isoformat()
    if interval == "week":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return day.strftime("%Y-%m")


def _generate_periods(date_from: date, date_to: date, interval: RevenueInterval) -> list[str]:
    """Sinh ĐỦ mọi nhãn khoảng thời gian trong `[date_from, date_to]`, kể cả
    khoảng KHÔNG có đơn hàng nào (điền doanh thu 0) - Chart.js cần trục thời
    gian liên tục, không bị "nhảy cóc" ở những ngày/tuần/tháng không phát
    sinh đơn. Duyệt TỪNG NGÀY (kể cả với interval "week"/"month") - đơn giản
    hơn hẳn tự tính bước nhảy theo tuần/tháng, chi phí không đáng kể ở quy mô
    dữ liệu 1 dashboard đồ án."""
    periods: list[str] = []
    seen: set[str] = set()
    current = date_from
    while current <= date_to:
        label = _period_label(current, interval)
        if label not in seen:
            seen.add(label)
            periods.append(label)
        current += timedelta(days=1)
    return periods


def build_summary_cache_key(date_from: date, date_to: date) -> str:
    return f"{DASHBOARD_CACHE_PREFIX}summary:{date_from.isoformat()}:{date_to.isoformat()}"


def build_revenue_cache_key(date_from: date, date_to: date, interval: RevenueInterval) -> str:
    return f"{DASHBOARD_CACHE_PREFIX}revenue:{date_from.isoformat()}:{date_to.isoformat()}:{interval}"


def build_top_products_cache_key(date_from: date, date_to: date, limit: int, sort_by: TopProductSortBy) -> str:
    return f"{DASHBOARD_CACHE_PREFIX}top-products:{date_from.isoformat()}:{date_to.isoformat()}:{limit}:{sort_by}"


def get_summary(db: Session, date_from: date, date_to: date) -> DashboardSummaryRead:
    orders_in_range = db.query(Order).filter(Order.created_at >= date_from, Order.created_at < _end_exclusive(date_to))
    total_orders = orders_in_range.count()

    total_revenue = (
        orders_in_range.filter(Order.status.in_(REVENUE_ELIGIBLE_STATUSES))
        .with_entities(func.sum(Order.total_amount))
        .scalar()
    )

    new_users = (
        db.query(User)
        .filter(
            User.role == UserRole.customer,
            User.created_at >= date_from,
            User.created_at < _end_exclusive(date_to),
        )
        .count()
    )

    return DashboardSummaryRead(
        date_from=date_from,
        date_to=date_to,
        total_revenue=total_revenue if total_revenue is not None else Decimal("0"),
        total_orders=total_orders,
        new_users=new_users,
    )


def get_revenue(db: Session, date_from: date, date_to: date, interval: RevenueInterval) -> list[RevenuePointRead]:
    rows = (
        db.query(Order.created_at, Order.total_amount)
        .filter(
            Order.status.in_(REVENUE_ELIGIBLE_STATUSES),
            Order.created_at >= date_from,
            Order.created_at < _end_exclusive(date_to),
        )
        .all()
    )

    revenue_by_period: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for created_at, total_amount in rows:
        revenue_by_period[_period_label(created_at.date(), interval)] += total_amount

    return [
        RevenuePointRead(period=period, revenue=revenue_by_period.get(period, Decimal("0")))
        for period in _generate_periods(date_from, date_to, interval)
    ]


def get_top_products(
    db: Session, date_from: date, date_to: date, *, limit: int, sort_by: TopProductSortBy
) -> list[TopProductRead]:
    """Nhóm theo `product_id` (KHÔNG theo `product_name` snapshot của
    `order_items`) - `name` trả về là tên HIỆN TẠI join từ bảng `products`
    (product_id FK `ondelete=RESTRICT` đảm bảo product luôn còn tồn tại nếu
    còn được tham chiếu bởi order_items, không hard-delete - xem
    app/models/product.py) - hợp lý hơn cho báo cáo Admin xem tên sản phẩm
    đang bán, khác nguyên tắc snapshot bất biến dùng cho HÓA ĐƠN (OrderItemRead)."""
    sort_expr = (
        func.sum(OrderItem.quantity) if sort_by == "quantity" else func.sum(OrderItem.quantity * OrderItem.price_at_purchase)
    )

    rows = (
        db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.quantity * OrderItem.price_at_purchase).label("revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.status.in_(REVENUE_ELIGIBLE_STATUSES),
            Order.created_at >= date_from,
            Order.created_at < _end_exclusive(date_to),
        )
        .group_by(OrderItem.product_id)
        .order_by(sort_expr.desc())
        .limit(limit)
        .all()
    )

    product_ids = [row.product_id for row in rows]
    name_by_id: dict[int, str] = {}
    if product_ids:
        name_by_id = dict(db.query(Product.id, Product.name).filter(Product.id.in_(product_ids)).all())

    return [
        TopProductRead(
            product_id=row.product_id,
            name=name_by_id.get(row.product_id, ""),
            quantity_sold=int(row.quantity_sold),
            revenue=row.revenue,
        )
        for row in rows
    ]
