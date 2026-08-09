"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { Order } from "@/types/order";

/**
 * Client Component (task 4.3.2, Screen 3 Stitch "Đặt hàng thành công") -
 * route `/checkout/success?order_id=<id>` (đề xuất đã thống nhất với user,
 * không dùng `/orders/[id]/confirmation`: đây là bước CUỐI nhất thời của
 * luồng checkout, không phải thuộc tính bền vững của resource đơn hàng -
 * xem thêm giải thích lúc đề xuất).
 *
 * Fetch LẠI `GET /orders/{id}` thay vì tin dữ liệu response `POST /orders`
 * (không truyền được qua điều hướng route) - cũng chịu được refresh/mở lại
 * link này sau đó, không chỉ hoạt động đúng 1 lần ngay sau khi đặt.
 *
 * KHÔNG hiển thị "Dự kiến giao hàng" (thiết kế Stitch có dòng này nhưng là
 * dữ liệu bịa - Backend không có field ước tính ngày giao, xem thảo luận lúc
 * audit thiết kế) - chỉ hiện dữ liệu THẬT từ response.
 */
export function OrderConfirmation() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!orderId) {
      setError("Thiếu mã đơn hàng.");
      setIsLoading(false);
      return;
    }
    api
      .get<ApiResponse<Order>>(`/orders/${orderId}`)
      .then(({ data }) => setOrder(data.data))
      .catch((err) => setError(extractApiErrorMessage(err, "Không tìm thấy đơn hàng.")))
      .finally(() => setIsLoading(false));
  }, [orderId]);

  if (isLoading) {
    return <div className="py-16 text-center text-foreground-muted">Đang tải đơn hàng...</div>;
  }

  if (error || !order) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-error">{error ?? "Không tìm thấy đơn hàng."}</p>
        <Link href="/products" className="rounded-full bg-primary px-6 py-3 font-heading text-sm text-background">
          Tiếp tục mua sắm
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6 rounded-xl bg-surface p-8 text-center shadow-warm md:p-10">
      <div className="flex h-24 w-24 items-center justify-center rounded-full bg-secondary-100">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary">
          <circle cx="12" cy="12" r="10" />
          <path d="m8 12 3 3 5-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <div className="space-y-2">
        <h1 className="font-heading text-2xl text-foreground md:text-3xl">Đặt hàng thành công!</h1>
        <p className="max-w-md text-foreground-secondary">
          Cảm ơn bạn đã mua sắm tại Vun. Đơn hàng của bạn <span className="font-semibold">#{order.id}</span> đang
          được xử lý.
        </p>
      </div>

      <div className="w-full rounded-lg bg-background p-4 text-left text-sm">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <span className="text-foreground-secondary">Tổng số tiền</span>
          <span className="font-heading text-lg text-primary">{formatPriceVnd(order.total_amount)}</span>
        </div>
        <div className="flex items-center justify-between pt-2">
          <span className="text-foreground-secondary">Giao đến</span>
          <span className="text-foreground">{order.shipping_name}</span>
        </div>
      </div>

      <div className="flex w-full flex-col gap-3 pt-2">
        <Link
          href="/orders"
          className="w-full rounded-2xl bg-primary py-3 font-heading text-sm text-background transition-colors hover:bg-primary-hover"
        >
          Xem đơn hàng của tôi
        </Link>
        <Link
          href="/products"
          className="w-full rounded-2xl border border-primary/30 py-3 font-heading text-sm text-primary transition-colors hover:bg-primary-100"
        >
          Tiếp tục mua sắm
        </Link>
      </div>
    </div>
  );
}
