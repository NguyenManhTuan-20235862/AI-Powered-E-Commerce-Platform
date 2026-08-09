"use client";

import Link from "next/link";

import { CartItemRow } from "@/components/cart/CartItemRow";
import { useCart } from "@/context/CartContext";
import { formatPriceVnd } from "@/lib/format";

/**
 * Client Component (task 4.3.2, Screen 1 Stitch "Giỏ hàng") - DÙNG LẠI
 * `CartContext` (task 4.3.1), KHÔNG tự fetch/giữ state riêng. Header/Footer
 * đã có sẵn qua `app/(customer)/layout.tsx` (bọc `CartProvider`) nên chỉ port
 * phần `<main>` của Stitch, không lặp lại nav/header của file gốc.
 */
export default function CartPage() {
  const { items, totalCount, totalPrice, isLoading } = useCart();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center text-foreground-muted">Đang tải giỏ hàng...</div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-4 py-20 text-center">
        <h1 className="font-heading text-2xl text-foreground">Giỏ hàng của bạn đang trống</h1>
        <p className="text-foreground-muted">Hãy khám phá các sản phẩm thủ công của Vun.</p>
        <Link
          href="/products"
          className="mt-2 rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
        >
          Tiếp tục mua sắm
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-4 py-10 lg:grid-cols-12">
      <div className="lg:col-span-8">
        <h1 className="mb-6 font-heading text-2xl text-foreground md:text-3xl">Giỏ hàng của bạn</h1>
        <div className="space-y-4">
          {items.map((item) => (
            <CartItemRow key={item.id} item={item} />
          ))}
        </div>
      </div>

      <div className="lg:col-span-4">
        <div className="sticky top-24 rounded-2xl bg-background p-6 shadow-warm">
          <h2 className="mb-4 border-b border-border pb-3 font-heading text-lg text-foreground">Tóm tắt đơn hàng</h2>
          <div className="mb-4 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary">Tạm tính ({totalCount} sản phẩm)</span>
              <span className="text-foreground">{formatPriceVnd(totalPrice)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary">Phí giao hàng</span>
              <span className="font-semibold text-secondary">Miễn phí</span>
            </div>
          </div>
          <div className="mb-4 flex items-center justify-between border-t border-border pt-4">
            <span className="font-heading text-foreground">Tổng cộng</span>
            <span className="font-heading text-xl text-primary">{formatPriceVnd(totalPrice)}</span>
          </div>
          <Link
            href="/checkout"
            className="flex w-full items-center justify-center rounded-2xl bg-primary py-4 font-heading text-sm text-background transition-colors hover:bg-primary-hover"
          >
            Tiến hành thanh toán
          </Link>
        </div>
      </div>
    </div>
  );
}
