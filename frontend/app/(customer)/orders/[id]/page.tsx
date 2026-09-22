import Link from "next/link";

import { OrderDetailView } from "@/components/order/OrderDetailView";

type Params = Promise<{ id: string }>;

/**
 * Trang chi tiết đơn hàng THẬT (trước đó chỉ stub tĩnh, xem lịch sử git) -
 * `page.tsx` (Server Component) CHỈ parse + validate `id` từ URL rồi giao cho
 * `OrderDetailView` (Client Component - cần state/effect cho fetch/SSE/hủy
 * đơn), cùng cách tách `OrdersPage`/`OrdersView`.
 *
 * `id` không phải số nguyên dương (VD `/orders/abc`) - báo "không tìm thấy"
 * NGAY tại đây, KHÔNG gọi xuống `OrderDetailView` (tránh gọi `GET /orders/abc`
 * biết trước sẽ luôn 422 - FastAPI tự validate `order_id: int` ở path param).
 */
export default async function OrderDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  const orderId = Number(id);

  if (!Number.isInteger(orderId) || orderId <= 0) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 py-16 text-center">
        <p className="text-foreground">Không tìm thấy đơn hàng này.</p>
        <Link href="/orders" className="text-sm font-semibold text-primary hover:underline">
          &larr; Quay lại danh sách đơn hàng
        </Link>
      </div>
    );
  }

  return <OrderDetailView orderId={orderId} />;
}
