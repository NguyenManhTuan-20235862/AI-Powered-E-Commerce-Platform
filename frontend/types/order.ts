// Khớp CHÍNH XÁC `OrderRead`/`OrderItemRead`/`OrderCreate` thật
// (backend/app/schemas/order.py, task 3.4.2 + shipping_name thêm ở task
// 4.3.2) - bản trước đây (camelCase, "completed" thay vì "delivered", thiếu
// shipping_*/note) là placeholder lệch hẳn, đã bị flag ở docs/KNOWN_TODOS.md #20.

export type OrderStatus = "pending" | "confirmed" | "shipping" | "delivered" | "cancelled";

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  // string, KHÔNG PHẢI number - cùng lý do Product.price/CartItem.unit_price:
  // Pydantic serialize Decimal thành string.
  price_at_purchase: string;
}

export interface Order {
  id: number;
  user_id: number;
  status: OrderStatus;
  total_amount: string;
  shipping_name: string;
  shipping_address: string;
  shipping_phone: string;
  note: string | null;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

// Payload POST /orders - snapshot lúc đặt, KHÔNG có payment_method (hệ thống
// hiện chỉ hỗ trợ COD, xem CLAUDE.md mục Notes).
export interface OrderCreatePayload {
  shipping_name: string;
  shipping_address: string;
  shipping_phone: string;
  note?: string;
}
