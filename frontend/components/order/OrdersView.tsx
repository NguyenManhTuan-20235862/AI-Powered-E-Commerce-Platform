"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { OrderCard } from "@/components/order/OrderCard";
import { OrderStatusFilter } from "@/components/order/OrderStatusFilter";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Order, OrderStatus } from "@/types/order";

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

  function goToPage(nextPage: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(nextPage));
    router.push(`/orders?${params.toString()}`);
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-2 font-heading text-2xl text-foreground md:text-3xl">Đơn hàng của tôi</h1>
      <p className="mb-6 text-foreground-muted">Theo dõi và quản lý các đơn hàng bạn đã đặt.</p>

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
