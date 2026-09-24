// Khớp CHÍNH XÁC `PaymentCreateRequest`/`PaymentCreateResponse`/`PaymentStatusRead`
// thật (backend/app/schemas/payment.py, task "Quyết định và hoàn thiện
// thanh toán") - thay placeholder cũ task 8.1.

export type PaymentStatus = "pending" | "success" | "failed" | "refunded";

export interface PaymentCreatePayload {
  order_id: number;
}

export interface PaymentCreateResult {
  payment_id: number;
  order_id: number;
  payment_url: string;
}

export interface Payment {
  order_id: number;
  payment_method: string;
  transaction_id: string | null;
  // string, KHÔNG PHẢI number - cùng lý do Order.total_amount/Product.price:
  // Pydantic serialize Decimal thành string.
  amount: string;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}
