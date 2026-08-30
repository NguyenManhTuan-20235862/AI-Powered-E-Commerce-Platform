// Khớp CHÍNH XÁC `DashboardSummaryRead`/`RevenuePointRead`/`TopProductRead`
// thật (backend/app/schemas/dashboard.py, task 5.3.1) - `total_revenue`/
// `revenue` khai `string` (KHÔNG PHẢI `number`) vì Backend serialize
// `Decimal` thành string (cùng quy ước `Order.total_amount`/`Product.price`
// ở types/order.ts, types/product.ts) - tránh lặp lại lỗi sai kiểu đã gặp ở
// `ProductRead`/`TopProductRead` cũ (docs/KNOWN_TODOS.md #14, `product_id`
// từng khai `str` trong khi cột thật là `BigInteger`).

export interface DashboardSummary {
  date_from: string;
  date_to: string;
  total_revenue: string;
  total_orders: number;
  new_users: number;
}

export type RevenueInterval = "day" | "week" | "month";

export interface RevenuePoint {
  period: string;
  revenue: string;
}

export type TopProductSortBy = "quantity" | "revenue";

export interface TopProduct {
  product_id: number;
  name: string;
  quantity_sold: number;
  revenue: string;
}
