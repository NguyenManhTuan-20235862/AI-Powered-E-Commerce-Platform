"use client";

import { AxiosError } from "axios";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { OrderStatusBadge } from "@/components/order/OrderStatusBadge";
import { useOrderStatusStream } from "@/hooks/useOrderStatusStream";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { OrderStatusEvent } from "@/types/notification";
import type { Order } from "@/types/order";
import type { Payment, PaymentCreateResult } from "@/types/payment";

const PAYMENT_STATUS_LABEL: Record<Payment["status"], string> = {
  pending: "Đang chờ thanh toán",
  success: "Đã thanh toán",
  failed: "Thanh toán thất bại",
  refunded: "Đã hoàn tiền",
};

type LoadState = "loading" | "ready" | "forbidden" | "not-found" | "network-error" | "error";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STREAM_BANNER_LABEL: Record<string, string | null> = {
  idle: null,
  connecting: null,
  open: null,
  reconnecting: "Mất kết nối cập nhật realtime, đang thử kết nối lại...",
  "retry-exhausted": "Mất kết nối cập nhật realtime.",
};

/**
 * Chi tiết 1 đơn hàng - trang chi tiết THẬT (trước đó chỉ stub tĩnh,
 * `app/(customer)/orders/[id]/page.tsx`). Client Component (cùng lý do
 * `OrdersView.tsx`: cần tương tác - hủy đơn, đồng bộ SSE ngay - hơn cần SEO).
 *
 * Phân biệt RÕ các loại lỗi HTTP (`GET /orders/{id}`, `app/routers/order.py`)
 * thay vì 1 thông báo lỗi chung chung:
 * - 401: KHÔNG tự xử lý ở đây (trước đây có `router.replace("/login")` riêng,
 *   ĐUA với chính điều hướng của `lib/axios.ts` - cùng 1 lúc 2 cơ chế redirect
 *   race nhau). Thống nhất về ĐÚNG 1 nơi (task "Dọn frontend để không còn màn
 *   hình giả") - `lib/axios.ts` interceptor tự phát hiện 401 không refresh
 *   được, tự điều hướng cứng `/login?session_expired=1` VÀ "bỏ rơi" promise
 *   (không bao giờ resolve/reject) - `fetchOrder()` không bao giờ vào nhánh
 *   catch cho case này, `loadState` giữ nguyên `"loading"` cho tới khi trình
 *   duyệt thật sự điều hướng đi (không còn hiện nhầm lỗi generic).
 * - 403: đã đăng nhập nhưng KHÔNG phải chủ đơn (`order.user_id != current_user.id`,
 *   xem `app/routers/order.py:get_order()`) - hiện thông báo + link quay lại
 *   danh sách, KHÔNG redirect (khác 401, đây không phải lỗi phiên đăng nhập).
 * - 404: đơn không tồn tại (id sai/đã bị xóa - thực tế Order không có xóa
 *   cứng nên chủ yếu là id không có thật).
 * - Lỗi mạng/5xx khác: có nút "Thử lại" (gọi lại fetchOrder(), KHÔNG có ý
 *   nghĩa cho 403/404 - lỗi đó KHÔNG tự hết khi gọi lại).
 *
 * **Khối "Thanh toán"** (task "Quyết định và hoàn thiện thanh toán") - fetch
 * RIÊNG `GET /payments/{orderId}/status`, best-effort (404 = đơn COD, chưa
 * từng khởi tạo thanh toán online - KHÔNG hiện khối này, không phải lỗi).
 * Có nút "Thanh toán lại qua VNPay" khi `payment.status` đang "pending"/
 * "failed" (Backend cho retry dùng LẠI đúng 1 dòng Payment, xem
 * `payment_service.py`) - gọi lại `POST /payments/create` rồi điều hướng
 * CỨNG (`window.location.href`) sang `payment_url` VNPay trả về.
 */
export function OrderDetailView({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [isPayingNow, setIsPayingNow] = useState(false);

  const fetchOrder = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const { data } = await api.get<ApiResponse<Order>>(`/orders/${orderId}`);
      setOrder(data.data);
      setLoadState("ready");
    } catch (err) {
      if (err instanceof AxiosError && err.response) {
        if (err.response.status === 403) {
          setLoadState("forbidden");
          return;
        }
        if (err.response.status === 404) {
          setLoadState("not-found");
          return;
        }
        setErrorMessage(extractApiErrorMessage(err, "Không thể tải đơn hàng. Vui lòng thử lại."));
        setLoadState("error");
        return;
      }
      // err.response undefined - mất mạng/không tới được server (khác lỗi
      // HTTP status thật ở trên), xem extractApiErrorMessage().
      setErrorMessage("Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và thử lại.");
      setLoadState("network-error");
    }
  }, [orderId]);

  useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  // Trạng thái thanh toán VNPay (task "Quyết định và hoàn thiện thanh toán")
  // - fetch RIÊNG, best-effort, KHÔNG ảnh hưởng `loadState` chính của đơn
  // hàng (404 ở đây nghĩa là "đơn COD, chưa từng khởi tạo thanh toán online"
  // - hoàn toàn BÌNH THƯỜNG, không phải lỗi cần hiện gì cho Customer, chỉ
  // đơn giản là KHÔNG hiện khối "Thanh toán" bên dưới).
  useEffect(() => {
    let active = true;
    api
      .get<ApiResponse<Payment>>(`/payments/${orderId}/status`)
      .then(({ data }) => {
        if (active) setPayment(data.data);
      })
      .catch(() => {
        if (active) setPayment(null);
      });
    return () => {
      active = false;
    };
  }, [orderId]);

  async function handlePayNow() {
    setIsPayingNow(true);
    try {
      const { data } = await api.post<ApiResponse<PaymentCreateResult>>("/payments/create", { order_id: orderId });
      window.location.href = data.data.payment_url;
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Không thể khởi tạo thanh toán VNPay. Vui lòng thử lại."));
      setIsPayingNow(false);
    }
  }

  async function handleCancel() {
    if (!order) return;
    if (!window.confirm(`Xác nhận hủy đơn hàng #${order.id}? Hành động này không thể hoàn tác.`)) return;
    setIsCancelling(true);
    try {
      const { data } = await api.put<ApiResponse<Order>>(`/orders/${order.id}/cancel`);
      setOrder(data.data);
      toast.success("Đã hủy đơn hàng");
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Hủy đơn hàng thất bại. Vui lòng thử lại."));
    } finally {
      setIsCancelling(false);
    }
  }

  // Đồng bộ SSE `/notifications/orders/stream` (task 5.2.1/5.2.2) trực tiếp
  // vào đơn đang xem - CHỈ xử lý event ĐÚNG order_id này (kênh Redis đã theo
  // user_id, 1 user có thể đang xem 1 đơn trong khi đơn KHÁC của họ đổi trạng
  // thái ở tab khác - lọc lại đây tránh refetch nhầm đơn không liên quan).
  // Refetch LẠI toàn bộ (KHÔNG tự patch `status` cục bộ) - cùng nguyên tắc
  // `OrdersView.tsx`/`OrderCard.tsx`: đảm bảo lấy đúng `updated_at` mới nhất
  // và toàn bộ snapshot thật từ Backend, không tự suy đoán 1 phần dữ liệu.
  const handleOrderStatusEvent = useCallback(
    (event: OrderStatusEvent) => {
      if (event.order_id !== orderId) return;
      fetchOrder();
    },
    [orderId, fetchOrder],
  );

  const { status: streamStatus, retryNow: retryStream } = useOrderStatusStream({
    enabled: loadState === "ready" || order !== null,
    onOrderStatus: handleOrderStatusEvent,
  });

  if (loadState === "loading") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center text-foreground-muted">Đang tải...</div>
    );
  }

  if (loadState === "forbidden") {
    return (
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 py-16 text-center">
        <p className="text-foreground">Bạn không có quyền xem đơn hàng này.</p>
        <Link href="/orders" className="text-sm font-semibold text-primary hover:underline">
          &larr; Quay lại danh sách đơn hàng
        </Link>
      </div>
    );
  }

  if (loadState === "not-found") {
    return (
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 py-16 text-center">
        <p className="text-foreground">Không tìm thấy đơn hàng này.</p>
        <Link href="/orders" className="text-sm font-semibold text-primary hover:underline">
          &larr; Quay lại danh sách đơn hàng
        </Link>
      </div>
    );
  }

  if (loadState === "network-error" || loadState === "error") {
    return (
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-4 py-16 text-center">
        <p className="text-error">{errorMessage}</p>
        <button
          type="button"
          onClick={fetchOrder}
          className="rounded-full bg-primary px-6 py-2 font-heading text-sm text-background hover:bg-primary-hover"
        >
          Thử lại
        </button>
      </div>
    );
  }

  if (!order) return null;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <Link href="/orders" className="mb-4 inline-block text-sm text-foreground-muted hover:text-foreground">
        &larr; Quay lại danh sách đơn hàng
      </Link>

      {STREAM_BANNER_LABEL[streamStatus] && (
        <div className="mb-4 flex items-center justify-between gap-2 rounded-lg bg-error-container px-4 py-3 text-error">
          <p className="text-sm font-semibold">{STREAM_BANNER_LABEL[streamStatus]}</p>
          {streamStatus === "retry-exhausted" && (
            <button type="button" onClick={retryStream} className="shrink-0 text-sm font-semibold underline hover:opacity-80">
              Kết nối lại
            </button>
          )}
        </div>
      )}

      <div className="flex flex-col gap-6 rounded-xl bg-surface p-6 shadow-warm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <h1 className="font-heading text-xl text-foreground md:text-2xl">Đơn hàng #{order.id}</h1>
            <p className="mt-1 text-sm text-foreground-muted">Đặt lúc {formatDateTime(order.created_at)}</p>
            <p className="text-sm text-foreground-muted">Cập nhật lúc {formatDateTime(order.updated_at)}</p>
          </div>
          <OrderStatusBadge status={order.status} />
        </div>

        <div>
          <h2 className="mb-3 font-heading text-lg text-primary">Sản phẩm</h2>
          <div className="flex flex-col divide-y divide-border">
            {order.items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-4 py-3">
                <div>
                  <p className="text-foreground">{item.product_name}</p>
                  <p className="text-sm text-foreground-muted">
                    {formatPriceVnd(item.price_at_purchase)} &times; {item.quantity}
                  </p>
                </div>
                <span className="whitespace-nowrap font-semibold text-foreground">
                  {formatPriceVnd(String(Number(item.price_at_purchase) * item.quantity))}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
            <span className="font-heading text-foreground">Tổng cộng</span>
            <span className="font-heading text-xl text-primary">{formatPriceVnd(order.total_amount)}</span>
          </div>
        </div>

        {/* Chỉ hiện khi đơn CÓ giao dịch VNPay (`payment !== null`) - đơn COD
            (chưa từng khởi tạo thanh toán online) KHÔNG hiện khối này, cùng
            nguyên tắc "không bịa dữ liệu không có thật" xuyên suốt dự án. */}
        {payment && (
          <div className="border-t border-border pt-4">
            <h2 className="mb-3 font-heading text-lg text-primary">Thanh toán</h2>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-background p-4 text-sm">
              <div className="flex flex-col gap-1">
                <span className="text-foreground-muted">
                  Phương thức: <span className="font-semibold uppercase text-foreground">{payment.payment_method}</span>
                </span>
                <span
                  className={`font-semibold ${
                    payment.status === "success"
                      ? "text-secondary"
                      : payment.status === "failed"
                        ? "text-error"
                        : "text-foreground-secondary"
                  }`}
                >
                  {PAYMENT_STATUS_LABEL[payment.status]}
                </span>
              </div>
              {(payment.status === "pending" || payment.status === "failed") && (
                <button
                  type="button"
                  onClick={handlePayNow}
                  disabled={isPayingNow}
                  className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isPayingNow ? "Đang chuyển hướng..." : "Thanh toán lại qua VNPay"}
                </button>
              )}
            </div>
          </div>
        )}

        <div className="border-t border-border pt-4">
          <h2 className="mb-3 font-heading text-lg text-primary">Thông tin giao hàng</h2>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm md:grid-cols-2">
            <div>
              <dt className="text-foreground-muted">Người nhận</dt>
              <dd className="text-foreground">{order.shipping_name}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Số điện thoại</dt>
              <dd className="text-foreground">{order.shipping_phone}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-foreground-muted">Địa chỉ</dt>
              <dd className="text-foreground">{order.shipping_address}</dd>
            </div>
            {order.note && (
              <div className="md:col-span-2">
                <dt className="text-foreground-muted">Ghi chú</dt>
                <dd className="text-foreground">{order.note}</dd>
              </div>
            )}
          </dl>
        </div>

        {order.status === "pending" && (
          <div className="border-t border-border pt-4">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling}
              className="rounded-full border border-error px-6 py-2 text-sm font-semibold text-error transition-colors hover:bg-error-container disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCancelling ? "Đang hủy..." : "Hủy đơn hàng"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
