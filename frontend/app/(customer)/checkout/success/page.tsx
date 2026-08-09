import { Suspense } from "react";

import { OrderConfirmation } from "@/components/checkout/OrderConfirmation";

// OrderConfirmation dùng useSearchParams() (đọc ?order_id=) - bắt buộc bọc
// Suspense, cùng lý do LoginForm (app/(auth)/login/page.tsx) - Next.js App
// Router yêu cầu Suspense boundary cho mọi component gọi useSearchParams.
export default function CheckoutSuccessPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Suspense fallback={<div className="py-16 text-center text-foreground-muted">Đang tải...</div>}>
        <OrderConfirmation />
      </Suspense>
    </div>
  );
}
