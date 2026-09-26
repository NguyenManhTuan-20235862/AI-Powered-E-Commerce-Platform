"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useCart } from "@/context/CartContext";
import { useAuth } from "@/hooks/useAuth";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd, resolveProductImageUrlClient } from "@/lib/format";
import { checkoutSchema, type CheckoutFormValues } from "@/lib/validations/checkout";
import type { ApiResponse } from "@/types/common";
import type { Order } from "@/types/order";
import type { PaymentCreateResult } from "@/types/payment";

type OrderApiResponse = ApiResponse<Order>;
type PaymentApiResponse = ApiResponse<PaymentCreateResult>;

type PaymentMethod = "cod" | "vnpay";

/**
 * Client Component (task 4.3.2, Screen 2 Stitch "Thanh toán"; VNPay thật ở
 * task "Quyết định và hoàn thiện thanh toán") - form giao hàng
 * (react-hook-form + zod, cùng pattern LoginForm/RegisterForm task 1.3.4) +
 * tóm tắt đơn hàng (đọc CartContext, KHÔNG tự fetch) + submit `POST /orders`.
 *
 * `paymentMethod` là state THUẦN FRONTEND (`useState`, KHÔNG gửi trong
 * `POST /orders`) - `OrderCreate` (Backend) vẫn KHÔNG có field
 * `payment_method` VÀ CỐ TÌNH không cần thêm: đặt hàng luôn tạo `Order`
 * giống hệt nhau bất kể phương thức (COD ngầm định, xem
 * `order_service.checkout()`) - "chọn VNPay" chỉ quyết định hành động NGAY
 * SAU khi đơn đã tạo xong: gọi thêm `POST /payments/create` rồi điều hướng
 * (redirect CỨNG, không phải `router.push`) sang `payment_url` VNPay trả về.
 * COD giữ NGUYÊN hành vi cũ (điều hướng `/checkout/success`).
 *
 * Momo VẪN decorative/"Sắp ra mắt" (quyết định đã xác nhận: "không nên làm
 * đồng thời VNPay và Momo - hoàn thiện 1 cổng tốt có giá trị hơn 2 cổng dở
 * dang") - CHỈ VNPay chuyển từ decorative sang chức năng thật.
 */
export function CheckoutForm() {
  const router = useRouter();
  const { user } = useAuth();
  const { items, totalCount, totalPrice, refreshCart } = useCart();
  const [serverError, setServerError] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cod");
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CheckoutFormValues>({ resolver: zodResolver(checkoutSchema) });

  // Pre-fill từ user (GET /auth/me qua useAuth()) - CHỈ chạy khi user vừa có
  // giá trị (load bất đồng bộ, chậm hơn lúc form mount) - dùng reset() thay
  // vì defaultValues (defaultValues chỉ đọc 1 lần lúc mount, user thường CHƯA
  // load xong tại thời điểm đó).
  useEffect(() => {
    if (!user) return;
    reset({
      shipping_name: user.fullName ?? "",
      shipping_phone: user.phone ?? "",
      shipping_address: user.address ?? "",
      note: "",
    });
  }, [user, reset]);

  async function onSubmit(values: CheckoutFormValues) {
    setServerError(null);
    try {
      const { data } = await api.post<OrderApiResponse>("/orders", {
        shipping_name: values.shipping_name,
        shipping_phone: values.shipping_phone,
        shipping_address: values.shipping_address,
        note: values.note || undefined,
      });
      const orderId = data.data.id;
      // Đơn hàng ĐÃ tạo thành công tại đây - Backend đã xóa cart_items thật
      // NGAY trong transaction checkout() - CartContext KHÔNG tự biết nên cần
      // đồng bộ lại badge Header/state cục bộ. Dùng refreshCart() (GET /cart,
      // chỉ ĐỌC) thay vì DELETE /cart: Backend đã xóa rồi nên gửi thêm DELETE
      // là THỪA + có race thật (nếu khách thêm món mới ở tab khác trong khoảng
      // này, DELETE đến muộn sẽ xóa nhầm cả món mới). GET trả đúng trạng thái
      // hiện tại (rỗng, hoặc chỉ còn món vừa thêm ở tab khác - không xóa nhầm).
      // Tách .catch (không await chặn luồng): lỗi đồng bộ badge KHÔNG phải lỗi
      // đặt hàng (đơn đã tạo xong thật), badge tự đúng ở lần fetch kế tiếp.
      refreshCart().catch(() => {});

      if (paymentMethod === "vnpay") {
        try {
          const payment = await api.post<PaymentApiResponse>("/payments/create", { order_id: orderId });
          // Điều hướng CỨNG (window.location.href, KHÔNG PHẢI router.push) -
          // payment_url là trang NGOÀI app (VNPay), router Next.js (điều
          // hướng nội bộ app) không xử lý được URL ngoài domain.
          window.location.href = payment.data.data.payment_url;
          return;
        } catch (paymentErr) {
          // Đơn ĐÃ tạo thành công (chỉ bước tạo giao dịch VNPay thất bại, VD
          // chưa cấu hình sandbox/503) - KHÔNG hiện "đặt hàng thất bại" (sai
          // sự thật, đơn đã tồn tại thật) - báo lỗi RIÊNG bằng toast rồi vẫn
          // đưa khách sang trang xác nhận đơn (COD-style fallback) - khách
          // xem được đơn ngay, thử thanh toán VNPay lại sau từ chi tiết đơn
          // (`OrderDetailView.tsx` có nút "Thanh toán lại" khi Payment đang
          // "pending"/"failed").
          toast.error(
            extractApiErrorMessage(
              paymentErr,
              "Không thể khởi tạo thanh toán VNPay. Đơn hàng vẫn được ghi nhận, bạn có thể thanh toán lại sau.",
            ),
          );
        }
      }

      router.push(`/checkout/success?order_id=${orderId}`);
    } catch (err) {
      // 409 (thiếu tồn kho, xem order_service.checkout()) và mọi lỗi khác
      // đều hiện message THẬT từ Backend (danh sách sản phẩm thiếu cụ thể),
      // không phải lỗi chung chung.
      setServerError(extractApiErrorMessage(err, "Đặt hàng thất bại. Vui lòng thử lại."));
    }
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
      <div className="flex flex-col gap-6 lg:col-span-7">
        <section className="rounded-xl bg-surface p-6 shadow-warm">
          <h2 className="mb-4 font-heading text-lg text-primary">Thông tin giao hàng</h2>
          <form id="checkout-form" onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="shipping_name" className="text-sm font-semibold text-foreground-secondary">
                  Họ và tên
                </label>
                <input
                  id="shipping_name"
                  type="text"
                  placeholder="Nhập họ và tên"
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
                  {...register("shipping_name")}
                />
                {errors.shipping_name && <p className="text-sm text-error">{errors.shipping_name.message}</p>}
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="shipping_phone" className="text-sm font-semibold text-foreground-secondary">
                  Số điện thoại
                </label>
                <input
                  id="shipping_phone"
                  type="tel"
                  placeholder="Nhập số điện thoại"
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
                  {...register("shipping_phone")}
                />
                {errors.shipping_phone && <p className="text-sm text-error">{errors.shipping_phone.message}</p>}
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="shipping_address" className="text-sm font-semibold text-foreground-secondary">
                Địa chỉ giao hàng
              </label>
              <textarea
                id="shipping_address"
                rows={3}
                placeholder="Nhập địa chỉ chi tiết"
                className="resize-none rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
                {...register("shipping_address")}
              />
              {errors.shipping_address && <p className="text-sm text-error">{errors.shipping_address.message}</p>}
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="note" className="text-sm font-semibold text-foreground-secondary">
                Ghi chú đơn hàng (Tùy chọn)
              </label>
              <textarea
                id="note"
                rows={2}
                placeholder="Ghi chú thêm..."
                className="resize-none rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
                {...register("note")}
              />
              {errors.note && <p className="text-sm text-error">{errors.note.message}</p>}
            </div>
          </form>
        </section>

        <section className="rounded-xl bg-surface p-6 shadow-warm">
          <h2 className="mb-4 font-heading text-lg text-primary">Phương thức thanh toán</h2>
          <div className="flex flex-col gap-3">
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border-2 p-4 ${
                paymentMethod === "cod" ? "border-primary bg-primary-100" : "border-border"
              }`}
            >
              <input
                type="radio"
                name="payment"
                checked={paymentMethod === "cod"}
                onChange={() => setPaymentMethod("cod")}
                className="h-5 w-5 text-primary"
              />
              <span className="font-semibold text-foreground">Thanh toán khi nhận hàng (COD)</span>
            </label>
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border-2 p-4 ${
                paymentMethod === "vnpay" ? "border-primary bg-primary-100" : "border-border"
              }`}
            >
              <input
                type="radio"
                name="payment"
                checked={paymentMethod === "vnpay"}
                onChange={() => setPaymentMethod("vnpay")}
                className="h-5 w-5 text-primary"
              />
              <span className="font-semibold text-foreground">Thanh toán qua VNPay</span>
            </label>
            {/* Momo VẪN decorative/"Sắp ra mắt" (quyết định đã xác nhận: không
                làm đồng thời VNPay và Momo) - CHỈ VNPay ở trên chuyển sang
                chức năng thật, radio này giữ nguyên disabled như cũ. */}
            <div className="flex cursor-not-allowed items-center justify-between rounded-lg border border-border p-4 opacity-60 grayscale">
              <div className="flex items-center gap-3">
                <input type="radio" disabled className="h-5 w-5" />
                <span className="text-foreground-secondary">Thanh toán qua Ví Momo</span>
              </div>
              <span className="rounded bg-background px-2 py-1 text-xs text-foreground-muted">Sắp ra mắt</span>
            </div>
          </div>
        </section>
      </div>

      <div className="lg:col-span-5">
        <div className="sticky top-24 flex flex-col gap-4 rounded-xl bg-surface p-6 shadow-warm">
          <h2 className="font-heading text-lg text-primary">Tóm tắt đơn hàng</h2>
          <div className="flex max-h-[320px] flex-col gap-3 overflow-y-auto pr-1">
            {items.map((item) => {
              const imageUrl = resolveProductImageUrlClient(item.product_image_url);
              return (
                <div key={item.id} className="flex items-center gap-3">
                  <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-background">
                    {imageUrl && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={imageUrl} alt={item.product_name} className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="flex-grow">
                    <h3 className="line-clamp-1 text-sm text-foreground">{item.product_name}</h3>
                    <p className="text-xs text-foreground-muted">SL: {item.quantity}</p>
                  </div>
                  <span className="whitespace-nowrap text-sm text-foreground">{formatPriceVnd(item.subtotal)}</span>
                </div>
              );
            })}
          </div>
          <div className="h-px bg-border" />
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between text-foreground-secondary">
              <span>Tạm tính ({totalCount} sản phẩm)</span>
              <span>{formatPriceVnd(totalPrice)}</span>
            </div>
            <div className="flex justify-between text-foreground-secondary">
              <span>Phí vận chuyển</span>
              <span className="font-semibold text-secondary">Miễn phí</span>
            </div>
          </div>
          <div className="h-px bg-border" />
          <div className="flex items-end justify-between">
            <span className="font-heading text-foreground">Tổng cộng</span>
            <span className="font-heading text-xl text-primary">{formatPriceVnd(totalPrice)}</span>
          </div>

          {serverError && (
            <p className="rounded-lg bg-error-container px-4 py-3 text-sm text-error" role="alert">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            form="checkout-form"
            disabled={isSubmitting}
            className="mt-1 flex w-full items-center justify-center rounded-2xl bg-primary py-4 font-heading text-base text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Đang xử lý..." : paymentMethod === "vnpay" ? "Đặt hàng & Thanh toán VNPay" : "Đặt hàng"}
          </button>
        </div>
      </div>
    </div>
  );
}
