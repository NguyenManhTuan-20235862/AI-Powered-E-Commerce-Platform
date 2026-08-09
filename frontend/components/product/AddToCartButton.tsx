"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { cartErrorMessage, useCart } from "@/context/CartContext";

/**
 * Client Component - nút "Thêm vào giỏ" dạng icon tròn ở ProductCard (catalog,
 * task 4.3.1), mặc định quantity=1. ProductCard vẫn là Server Component, chỉ
 * tách riêng phần tương tác này (cùng cách tách QuantitySelector/SortDropdown
 * trước đó).
 *
 * Nút này nằm LỒNG BÊN TRONG `<Link>` bọc cả ProductCard (điều hướng sang
 * trang chi tiết) - `<button>` trong `<a>` không hợp lệ HTML5 thuần túy, nhưng
 * KHÔNG gây lỗi/warning gì ở React (cây DOM dựng trực tiếp qua createElement,
 * không qua parse chuỗi HTML nên không có chuyện browser tự đóng thẻ sai chỗ)
 * - `preventDefault()` + `stopPropagation()` chặn cả hành vi điều hướng mặc
 * định của `<a>` LẪN handler điều hướng nội bộ của Next `<Link>` (chính nó
 * cũng chỉ là 1 listener onClick gắn trên cùng thẻ `<a>`).
 */
export function AddToCartButton({ productId, disabled = false }: { productId: number; disabled?: boolean }) {
  const router = useRouter();
  const { addItem, isAuthenticated } = useCart();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast.error("Vui lòng đăng nhập để thêm vào giỏ hàng");
      router.push("/login");
      return;
    }

    setIsSubmitting(true);
    try {
      await addItem(productId, 1);
      toast.success("Đã thêm vào giỏ hàng");
    } catch (err) {
      toast.error(cartErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isSubmitting}
      aria-label="Thêm vào giỏ hàng"
      className="flex h-10 w-10 items-center justify-center rounded-full bg-background text-foreground-muted transition-colors hover:bg-primary hover:text-background disabled:cursor-not-allowed disabled:opacity-60"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="9" cy="21" r="1.4" />
        <circle cx="18" cy="21" r="1.4" />
        <path d="M2.5 3h2l2.6 12.6a1.8 1.8 0 0 0 1.8 1.4h8.4a1.8 1.8 0 0 0 1.75-1.4L21.5 8H6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
