// Khớp ĐÚNG wire protocol thật của Backend GET /notifications/orders/stream
// (task 5.2.1, backend/app/routers/notification.py) - SSE dùng "event: <tên>"
// riêng cho từng loại (KHÔNG đi qua EventSource.onmessage - đó chỉ nhận event
// KHÔNG tên "event:", phải addEventListener() theo đúng tên event), khác hẳn
// /ws/chat (task 5.1.1) gói loại event vào field "type" bên trong 1 JSON
// duy nhất qua onmessage.

import type { OrderStatus } from "@/types/order";

// event: "connected" - xác nhận subscribe Redis đã sẵn sàng (app/routers/notification.py).
export interface OrderStreamConnectedEvent {
  user_id: number;
}

// event: "order_status" - publish sau PUT /orders/{id}/status thành công
// (app/services/notification_service.py:publish_order_status_update()).
export interface OrderStatusEvent {
  order_id: number;
  status: OrderStatus;
  timestamp: string;
}

// Không có trạng thái "reconnecting theo backoff tăng dần" như
// ChatConnectionStatus (WebSocket, task 5.1.2) - EventSource tự quản lý thời
// gian retry (KHÔNG viết tay), hook chỉ cần phản ánh readyState + 1 guard
// token hết hạn (xem hooks/useOrderStatusStream.ts).
export type OrderStreamStatus = "idle" | "connecting" | "open" | "reconnecting" | "retry-exhausted";
