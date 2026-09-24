import { Suspense } from "react";

import { PaymentResult } from "@/components/checkout/PaymentResult";

// PaymentResult dùng useSearchParams() (đọc ?order_id=/?status=) - bắt buộc
// bọc Suspense, cùng lý do OrderConfirmation (app/(customer)/checkout/success/page.tsx).
export default function PaymentResultPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Suspense fallback={<div className="py-16 text-center text-foreground-muted">Đang tải...</div>}>
        <PaymentResult />
      </Suspense>
    </div>
  );
}
