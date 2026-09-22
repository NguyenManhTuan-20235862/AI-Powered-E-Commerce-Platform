import { Suspense } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { OrdersView } from "@/components/order/OrdersView";

// OrdersView dùng useSearchParams() (đọc ?status=/?page=) - bắt buộc bọc
// Suspense, cùng lý do LoginForm/OrderConfirmation - Next.js App Router yêu
// cầu Suspense boundary cho mọi component gọi hook này.
//
// RequireAuth bọc NGOÀI Suspense - chặn TRƯỚC khi OrdersView kịp mount/gọi
// GET /orders lúc chưa đăng nhập (trước đây: request 401 không xử lý riêng,
// `orders` giữ nguyên [] sau finally -> hiện nhầm "Bạn chưa có đơn hàng nào"
// thay vì đưa về /login).
export default function OrdersPage() {
  return (
    <RequireAuth>
      <Suspense fallback={<div className="py-16 text-center text-foreground-muted">Đang tải...</div>}>
        <OrdersView />
      </Suspense>
    </RequireAuth>
  );
}
