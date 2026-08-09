"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { useCart } from "@/context/CartContext";

/**
 * Client Component (task 4.3.2) - chỉ lo guard giỏ hàng trống (điều hướng
 * thẳng vào `/checkout` khi chưa có gì để đặt sẽ 409 ngay lúc submit, chặn
 * SỚM ở đây cho trải nghiệm rõ ràng hơn) + layout - phần form/logic đặt hàng
 * thật nằm ở `CheckoutForm` (tách riêng để test độc lập, cùng pattern
 * AddToCartSection task 4.3.1).
 *
 * `hasCheckedCart` - guard CHỈ chạy ĐÚNG 1 LẦN ngay sau khi `CartContext`
 * load xong, KHÔNG re-check mỗi khi `items` đổi. Bug thật đã tự gặp lúc
 * verify: `CheckoutForm` gọi `clearCart()` SAU KHI đặt hàng thành công (xóa
 * giỏ hàng thật) rồi mới `router.push("/checkout/success?...")` - nếu effect
 * này chạy lại theo `items.length` (dependency cũ), `items` vừa về 0 do
 * `clearCart()` sẽ khiến effect tưởng nhầm "giỏ hàng trống" và
 * `router.replace("/cart")`, ĐUA (race) với điều hướng sang trang xác nhận
 * và THẮNG - kết quả sai: đặt hàng thành công nhưng bị đá về `/cart` thay vì
 * trang xác nhận. Chỉ check 1 lần lúc mount/load xong tránh đúng race này.
 */
export default function CheckoutPage() {
  const router = useRouter();
  const { items, isLoading } = useCart();
  const [hasCheckedCart, setHasCheckedCart] = useState(false);

  useEffect(() => {
    if (isLoading || hasCheckedCart) return;
    setHasCheckedCart(true);
    if (items.length === 0) {
      toast.error("Giỏ hàng đang trống - vui lòng thêm sản phẩm trước khi thanh toán");
      router.replace("/cart");
    }
  }, [isLoading, hasCheckedCart, items.length, router]);

  if (isLoading || !hasCheckedCart || items.length === 0) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 text-center text-foreground-muted">Đang tải...</div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="mb-8 text-center font-heading text-2xl text-foreground md:text-3xl">Thanh toán</h1>
      <CheckoutForm />
    </div>
  );
}
