"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { cartErrorMessage, useCart } from "@/context/CartContext";
import { formatPriceVnd, resolveProductImageUrlClient } from "@/lib/format";
import type { CartItem } from "@/types/cart";

/**
 * Client Component - 1 dòng sản phẩm trong giỏ hàng (task 4.3.2, Screen 1
 * Stitch). Nút +/- gọi `updateQuantity` NGAY khi bấm (không debounce) - thiết
 * kế Stitch chỉ có nút bấm, không có ô nhập số tay, nên "chỉ gọi khi xác
 * nhận" ở đây nghĩa là mỗi lần bấm = 1 lần xác nhận, disable cả 2 nút trong
 * lúc chờ response để tránh bấm dồn dập gây race giữa các request.
 *
 * `stock_quantity`/`is_active` là dữ liệu LIVE trả về cùng `CartItemRead`
 * (không phải snapshot lúc thêm) - dùng để cảnh báo ngay tại dòng nếu sản
 * phẩm đã hết hàng/ngừng bán SAU KHI đã có trong giỏ, thay vì để khách phát
 * hiện muộn lúc bấm "Đặt hàng" (409 ở checkout).
 */
export function CartItemRow({ item }: { item: CartItem }) {
  const { updateQuantity, removeItem } = useCart();
  const [isPending, setIsPending] = useState(false);
  const imageUrl = resolveProductImageUrlClient(item.product_image_url);
  const unavailable = !item.is_active || item.stock_quantity <= 0;

  async function handleQuantityChange(nextQuantity: number) {
    if (nextQuantity < 1 || isPending) return;
    setIsPending(true);
    try {
      await updateQuantity(item.id, nextQuantity);
    } catch (err) {
      toast.error(cartErrorMessage(err));
    } finally {
      setIsPending(false);
    }
  }

  async function handleRemove() {
    if (isPending) return;
    setIsPending(true);
    try {
      await removeItem(item.id);
      toast.success("Đã xóa sản phẩm khỏi giỏ hàng");
    } catch (err) {
      toast.error(cartErrorMessage(err));
      setIsPending(false);
    }
  }

  return (
    <div className="relative flex flex-col items-center gap-4 rounded-xl bg-surface p-4 shadow-sm transition-shadow hover:shadow-warm sm:flex-row">
      <button
        type="button"
        onClick={handleRemove}
        disabled={isPending}
        aria-label="Xóa sản phẩm"
        className="absolute right-4 top-4 text-foreground-muted transition-colors hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
        </svg>
      </button>

      {imageUrl ? (
        // <img> thường, không phải next/image - xem giải thích ở
        // lib/format.ts:resolveProductImageUrlClient().
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt={item.product_name} className="h-24 w-24 rounded-lg object-cover" />
      ) : (
        <div className="flex h-24 w-24 items-center justify-center rounded-lg bg-background text-foreground-muted">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="9" cy="9" r="2" />
            <path d="M21 15l-5-5L5 21" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      )}

      <div className="flex w-full flex-grow flex-col justify-between gap-2 sm:h-24">
        <div>
          <Link href={`/products/${item.product_slug}`} className="font-heading text-base text-foreground hover:text-primary">
            {item.product_name}
          </Link>
          {unavailable && (
            <p className="mt-1 text-sm font-semibold text-error">
              {!item.is_active ? "Sản phẩm đã ngừng kinh doanh" : "Sản phẩm đã hết hàng"}
            </p>
          )}
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center rounded-full border border-border bg-background">
            <button
              type="button"
              onClick={() => handleQuantityChange(item.quantity - 1)}
              disabled={isPending || item.quantity <= 1}
              aria-label="Giảm số lượng"
              className="px-3 py-1 text-foreground-secondary transition-colors hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              -
            </button>
            <span className="w-8 text-center font-body text-sm">{item.quantity}</span>
            <button
              type="button"
              onClick={() => handleQuantityChange(item.quantity + 1)}
              disabled={isPending || (item.stock_quantity > 0 && item.quantity >= item.stock_quantity)}
              aria-label="Tăng số lượng"
              className="px-3 py-1 text-foreground-secondary transition-colors hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              +
            </button>
          </div>
          <span className="font-heading text-lg text-primary">{formatPriceVnd(item.subtotal)}</span>
        </div>
      </div>
    </div>
  );
}
