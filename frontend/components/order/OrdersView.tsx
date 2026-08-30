"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { OrderCard } from "@/components/order/OrderCard";
import { OrderStatusFilter } from "@/components/order/OrderStatusFilter";
import { useOrderStatusStream } from "@/hooks/useOrderStatusStream";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { OrderStatusEvent, OrderStreamStatus } from "@/types/notification";
import type { Order, OrderStatus } from "@/types/order";

// Nhãn hiển thị cho toast - cùng nội dung `OrderStatusBadge.tsx`/
// `OrderStatusFilter.tsx` (2 file đó cũng tự khai map riêng, không có 1 nguồn
// chung sẵn có trong dự án - giữ đúng pattern đã có, không thêm trừu tượng
// mới cho 1 map 5 dòng).
const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  shipping: "Đang giao",
  delivered: "Đã giao",
  cancelled: "Đã hủy",
};

const STREAM_BANNER_LABEL: Record<OrderStreamStatus, string | null> = {
  idle: null,
  connecting: null,
  open: null,
  reconnecting: "Mất kết nối cập nhật realtime, đang thử kết nối lại...",
  "retry-exhausted": "Mất kết nối cập nhật realtime.",
};

/**
 * Client Component (task 4.3.3) - CSR thay vì SSR: trang này cần tương tác
 * nhiều (đổi tab lọc, hủy đơn, cập nhật lại danh sách NGAY không reload cả
 * trang) hơn là cần SEO (trang cá nhân, luôn yêu cầu đăng nhập, không có ý
 * nghĩa để công cụ tìm kiếm index) - đánh đổi ngược lại với `/products`
 * (SSR, task 4.2.1) vốn ưu tiên SEO cho trang catalog công khai. Tab lọc vẫn
 * dùng URL `?status=` làm nguồn sự thật (cùng pattern `ProductFilters`) để
 * giữ được share link/back-forward, chỉ khác là DATA re-fetch qua `useEffect`
 * gọi thẳng `api` (axios) thay vì Next.js tự re-render Server Component theo
 * URL như trang `/products`.
 *
 * Tách riêng khỏi `app/(customer)/orders/page.tsx` vì dùng `useSearchParams()`
 * - Next.js App Router bắt buộc bọc `<Suspense>` cho mọi component gọi hook
 * này (cùng lý do `LoginForm`/`OrderConfirmation`), `page.tsx` chỉ còn nhiệm
 * vụ bọc Suspense, không tự chứa logic.
 */
export function OrdersView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const status = searchParams.get("status") as OrderStatus | null;
  const page = Number(searchParams.get("page") ?? "1");

  const [orders, setOrders] = useState<Order[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 10 };
      if (status) params.status = status;
      const { data } = await api.get<ApiResponse<PaginatedResponse<Order>>>("/orders", { params });
      setOrders(data.data.items);
      setTotalPages(data.data.total_pages);
    } finally {
      setIsLoading(false);
    }
  }, [status, page]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // SSE `/notifications/orders/stream` (task 5.2.2) - CHỈ mở trong lúc đứng
  // ở trang này (page-scoped, xác nhận trước khi code) - nhận sự kiện thì
  // gọi LẠI `fetchOrders()` đã có (KHÔNG tự patch state cục bộ) - cùng lý do
  // `onCancelled` ở `OrderCard`: đơn vừa đổi trạng thái có thể không còn
  // khớp tab `?status=` đang lọc, refetch đảm bảo danh sách luôn đúng thay
  // vì để lại dòng lệch trạng thái.
  const handleOrderStatusEvent = useCallback(
    (event: OrderStatusEvent) => {
      toast.info(`Đơn hàng #${event.order_id}: ${STATUS_LABEL[event.status]}`);
      fetchOrders();
    },
    [fetchOrders],
  );

  const { status: streamStatus, retryNow: retryStream } = useOrderStatusStream({
    enabled: true,
    onOrderStatus: handleOrderStatusEvent,
  });

  function goToPage(nextPage: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(nextPage));
    router.push(`/orders?${params.toString()}`);
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-2 font-heading text-2xl text-foreground md:text-3xl">Đơn hàng của tôi</h1>
      <p className="mb-6 text-foreground-muted">Theo dõi và quản lý các đơn hàng bạn đã đặt.</p>

      {STREAM_BANNER_LABEL[streamStatus] && (
        <div className="mb-6 flex items-center justify-between gap-2 rounded-lg bg-error-container px-4 py-3 text-error">
          <p className="text-sm font-semibold">{STREAM_BANNER_LABEL[streamStatus]}</p>
          {streamStatus === "retry-exhausted" && (
            <button type="button" onClick={retryStream} className="shrink-0 text-sm font-semibold underline hover:opacity-80">
              Kết nối lại
            </button>
          )}
        </div>
      )}

      <div className="mb-6">
        <OrderStatusFilter />
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-foreground-muted">Đang tải...</div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <p className="text-foreground-muted">
            {status ? "Không có đơn hàng nào khớp bộ lọc này." : "Bạn chưa có đơn hàng nào."}
          </p>
          <Link
            href="/products"
            className="mt-1 rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
          >
            Tiếp tục mua sắm
          </Link>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {orders.map((order) => (
              <OrderCard key={order.id} order={order} onCancelled={fetchOrders} />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
              >
                Trang trước
              </button>
              <span className="text-sm text-foreground-muted">
                Trang {page}/{totalPages}
              </span>
              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
                className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
              >
                Trang sau
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
