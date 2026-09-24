"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { Order } from "@/types/order";
import type { Payment, PaymentCreateResult } from "@/types/payment";

type LoadState = "loading" | "ready" | "invalid" | "error";

/**
 * Client Component - trang kết quả thanh toán VNPay (task "Quyết định và
 * hoàn thiện thanh toán") - route `/checkout/payment-result?order_id=<id>&status=<...>`,
 * target Backend redirect TỚI sau khi xử lý xong `GET /payments/callback`
 * (xem `app/routers/payment.py:payment_callback()`).
 *
 * `?status=` trên URL CHỈ dùng để hiện nhãn "lạc quan" (optimistic) trong
 * lúc đang fetch - KHÔNG tin để hiển thị KẾT QUẢ CUỐI CÙNG (cùng nguyên tắc
 * `OrderConfirmation.tsx`: không truyền qua điều hướng được an toàn, và
 * trang cần chịu được refresh/mở lại link sau đó) - LUÔN fetch LẠI
 * `GET /payments/{order_id}/status` (nguồn sự thật DUY NHẤT) trước khi hiện
 * kết quả thật.
 *
 * `?status=invalid` (hoặc thiếu `order_id`) - Backend không xác minh được
 * callback (chữ ký sai/số tiền lệch/không tìm thấy giao dịch) - hiện thông
 * báo chung, KHÔNG cố fetch gì (không có `order_id` đáng tin để fetch).
 */
export function PaymentResult() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const optimisticStatus = searchParams.get("status");

  const [order, setOrder] = useState<Order | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchResult = useCallback(async () => {
    if (!orderId || optimisticStatus === "invalid") {
      setLoadState("invalid");
      return;
    }
    setLoadState("loading");
    try {
      const [orderRes, paymentRes] = await Promise.all([
        api.get<ApiResponse<Order>>(`/orders/${orderId}`),
        api.get<ApiResponse<Payment>>(`/payments/${orderId}/status`),
      ]);
      setOrder(orderRes.data.data);
      setPayment(paymentRes.data.data);
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [orderId, optimisticStatus]);

  useEffect(() => {
    fetchResult();
  }, [fetchResult]);

  async function handleRetryPayment() {
    if (!orderId) return;
    setIsRetrying(true);
    try {
      const { data } = await api.post<ApiResponse<PaymentCreateResult>>("/payments/create", {
        order_id: Number(orderId),
      });
      window.location.href = data.data.payment_url;
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Không thể khởi tạo lại thanh toán. Vui lòng thử lại."));
      setIsRetrying(false);
    }
  }

  if (loadState === "loading") {
    return <div className="py-16 text-center text-foreground-muted">Đang xác nhận kết quả thanh toán...</div>;
  }

  if (loadState === "invalid") {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <h1 className="font-heading text-2xl text-foreground">Không thể xác minh giao dịch</h1>
        <p className="max-w-md text-foreground-secondary">
          Liên kết kết quả thanh toán không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra lại trong mục đơn hàng của bạn.
        </p>
        <Link href="/orders" className="rounded-full bg-primary px-6 py-3 font-heading text-sm text-background">
          Xem đơn hàng của tôi
        </Link>
      </div>
    );
  }

  if (loadState === "error" || !order || !payment) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-error">Không tải được kết quả thanh toán.</p>
        <button
          type="button"
          onClick={fetchResult}
          className="rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
        >
          Thử lại
        </button>
      </div>
    );
  }

  const isSuccess = payment.status === "success";
  const isFailed = payment.status === "failed";

  return (
    <div className="flex flex-col items-center gap-6 rounded-xl bg-surface p-8 text-center shadow-warm md:p-10">
      <div
        className={`flex h-24 w-24 items-center justify-center rounded-full ${
          isSuccess ? "bg-secondary-100" : isFailed ? "bg-error-container" : "bg-primary-100"
        }`}
      >
        {isSuccess ? (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary">
            <circle cx="12" cy="12" r="10" />
            <path d="m8 12 3 3 5-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : isFailed ? (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-error">
            <circle cx="12" cy="12" r="10" />
            <path d="m9 9 6 6M15 9l-6 6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>

      <div className="space-y-2">
        <h1 className="font-heading text-2xl text-foreground md:text-3xl">
          {isSuccess ? "Thanh toán thành công!" : isFailed ? "Thanh toán thất bại" : "Đang chờ xác nhận thanh toán"}
        </h1>
        <p className="max-w-md text-foreground-secondary">
          {isSuccess && (
            <>
              Đơn hàng <span className="font-semibold">#{order.id}</span> đã được thanh toán qua VNPay.
            </>
          )}
          {isFailed && (
            <>
              Giao dịch VNPay cho đơn <span className="font-semibold">#{order.id}</span> không thành công. Bạn có thể
              thử thanh toán lại hoặc chọn thanh toán khi nhận hàng.
            </>
          )}
          {!isSuccess && !isFailed && (
            <>
              Chưa nhận được kết quả cuối cùng từ VNPay cho đơn <span className="font-semibold">#{order.id}</span> -
              vui lòng kiểm tra lại sau ít phút.
            </>
          )}
        </p>
      </div>

      <div className="w-full rounded-lg bg-background p-4 text-left text-sm">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <span className="text-foreground-secondary">Số tiền</span>
          <span className="font-heading text-lg text-primary">{formatPriceVnd(payment.amount)}</span>
        </div>
        <div className="flex items-center justify-between pt-2">
          <span className="text-foreground-secondary">Trạng thái thanh toán</span>
          <span className="font-semibold text-foreground">
            {isSuccess ? "Đã thanh toán" : isFailed ? "Thất bại" : "Đang chờ"}
          </span>
        </div>
      </div>

      <div className="flex w-full flex-col gap-3 pt-2">
        {!isSuccess && (
          <button
            type="button"
            onClick={handleRetryPayment}
            disabled={isRetrying}
            className="w-full rounded-2xl bg-primary py-3 font-heading text-sm text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRetrying ? "Đang chuyển hướng..." : "Thanh toán lại qua VNPay"}
          </button>
        )}
        <Link
          href="/orders"
          className="w-full rounded-2xl border border-primary/30 py-3 font-heading text-sm text-primary transition-colors hover:bg-primary-100"
        >
          Xem đơn hàng của tôi
        </Link>
      </div>
    </div>
  );
}
