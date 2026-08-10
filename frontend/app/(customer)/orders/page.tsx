import { Suspense } from "react";

import { OrdersView } from "@/components/order/OrdersView";

// OrdersView dùng useSearchParams() (đọc ?status=/?page=) - bắt buộc bọc
// Suspense, cùng lý do LoginForm/OrderConfirmation - Next.js App Router yêu
// cầu Suspense boundary cho mọi component gọi hook này.
export default function OrdersPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-foreground-muted">Đang tải...</div>}>
      <OrdersView />
    </Suspense>
  );
}
