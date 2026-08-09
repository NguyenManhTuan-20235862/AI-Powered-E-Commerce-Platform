"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { useCart } from "@/context/CartContext";
import { useAuth } from "@/hooks/useAuth";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd, resolveProductImageUrlClient } from "@/lib/format";
import { checkoutSchema, type CheckoutFormValues } from "@/lib/validations/checkout";
import type { ApiResponse } from "@/types/common";
import type { Order } from "@/types/order";

type OrderApiResponse = ApiResponse<Order>;

/**
 * Client Component (task 4.3.2, Screen 2 Stitch "Thanh toán") - form giao
 * hàng (react-hook-form + zod, cùng pattern LoginForm/RegisterForm task
 * 1.3.4) + tóm tắt đơn hàng (đọc CartContext, KHÔNG tự fetch) + submit
 * `POST /orders`.
 *
 * KHÔNG có field payment_method - hệ thống hiện chỉ hỗ trợ COD (Payment
 * sandbox VNPay/Momo là task 8.1, chưa làm), `OrderCreate` (Backend) cũng
 * không có field này - COD ngầm định, radio VNPay/Momo chỉ hiển thị dạng
 * disabled/"Sắp ra mắt" đúng thiết kế Stitch, không có state/onChange thật.
 */
export function CheckoutForm() {
  const router = useRouter();
  const { user } = useAuth();
  const { items, totalCount, totalPrice, clearCart } = useCart();
  const [serverError, setServerError] = useState<string | null>(null);
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
      // Đơn hàng ĐÃ tạo thành công tại đây - điều hướng sang trang xác nhận
      // NGAY, không đợi clearCart() xong. Backend đã xóa cart_items thật lúc
      // checkout() - CartContext KHÔNG tự biết điều này (không có cơ chế nào
      // re-fetch sau 1 request không liên quan tới /cart) nên vẫn cần gọi
      // clearCart() để đồng bộ lại badge Header/state cục bộ, NHƯNG tách
      // riêng try/catch: nếu chính request DELETE /cart bị lỗi mạng thoáng
      // qua, KHÔNG được hiện lại "đặt hàng thất bại" (đơn đã tạo xong thật -
      // lỗi dọn dẹp cache cục bộ không phải lỗi đặt hàng, badge Header sẽ tự
      // đúng lại ở lần fetch giỏ hàng kế tiếp).
      router.push(`/checkout/success?order_id=${data.data.id}`);
      clearCart().catch(() => {});
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
            <label className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-primary bg-primary-100 p-4">
              <input type="radio" name="payment" checked readOnly className="h-5 w-5 text-primary" />
              <span className="font-semibold text-foreground">Thanh toán khi nhận hàng (COD)</span>
            </label>
            {["Thanh toán qua VNPay", "Thanh toán qua Ví Momo"].map((label) => (
              <div
                key={label}
                className="flex cursor-not-allowed items-center justify-between rounded-lg border border-border p-4 opacity-60 grayscale"
              >
                <div className="flex items-center gap-3">
                  <input type="radio" disabled className="h-5 w-5" />
                  <span className="text-foreground-secondary">{label}</span>
                </div>
                <span className="rounded bg-background px-2 py-1 text-xs text-foreground-muted">Sắp ra mắt</span>
              </div>
            ))}
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
            {isSubmitting ? "Đang đặt hàng..." : "Đặt hàng"}
          </button>
        </div>
      </div>
    </div>
  );
}
