"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { QuantitySelector } from "@/components/product/QuantitySelector";
import { cartErrorMessage, useCart } from "@/context/CartContext";

/**
 * Client Component - gộp QuantitySelector + nút "Thêm vào giỏ" ở trang chi
 * tiết (task 4.3.1). Tách riêng khỏi `ProductInfo` (vẫn Server Component) vì
 * cần giữ `quantity` cục bộ để truyền đúng số lượng đã chọn lúc gọi `addItem`.
 */
export function AddToCartSection({
  productId,
  stockQuantity,
}: {
  productId: number;
  stockQuantity: number;
}) {
  const router = useRouter();
  const { addItem, isAuthenticated } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inStock = stockQuantity > 0;

  async function handleAddToCart() {
    if (!isAuthenticated) {
      toast.error("Vui lòng đăng nhập để thêm vào giỏ hàng");
      router.push("/login");
      return;
    }

    setIsSubmitting(true);
    try {
      await addItem(productId, quantity);
      toast.success("Đã thêm vào giỏ hàng");
    } catch (err) {
      toast.error(cartErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mb-8 flex items-center gap-4">
      <QuantitySelector quantity={quantity} onChange={setQuantity} max={stockQuantity} />
      <button
        type="button"
        onClick={handleAddToCart}
        disabled={!inStock || isSubmitting}
        className="flex h-14 flex-grow items-center justify-center gap-2 rounded-2xl bg-primary font-heading text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:bg-foreground-muted disabled:opacity-60"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <path d="M6 7h15l-1.5 9h-12L6 7Zm0 0L5 3H2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="9.5" cy="20" r="1.2" />
          <circle cx="17.5" cy="20" r="1.2" />
        </svg>
        {!inStock ? "Hết hàng" : isSubmitting ? "Đang thêm..." : "Thêm vào giỏ"}
      </button>
    </div>
  );
}
