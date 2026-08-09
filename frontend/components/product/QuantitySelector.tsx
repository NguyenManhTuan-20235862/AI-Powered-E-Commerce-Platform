"use client";

import { useState } from "react";

/**
 * Client Component - state +/- thuần UI, CHƯA nối logic giỏ hàng thật (task
 * 4.3). `max` (tồn kho) chỉ để chặn chọn số lượng vô lý ngay trên UI - không
 * gọi API nào.
 */
export function QuantitySelector({ max }: { max?: number }) {
  const [quantity, setQuantity] = useState(1);
  const hasMax = typeof max === "number" && max > 0;

  function decrement() {
    setQuantity((q) => Math.max(1, q - 1));
  }

  function increment() {
    setQuantity((q) => (hasMax ? Math.min(max as number, q + 1) : q + 1));
  }

  return (
    <div className="flex h-14 w-32 items-center rounded-2xl border border-border bg-surface">
      <button
        type="button"
        onClick={decrement}
        disabled={quantity <= 1}
        aria-label="Giảm số lượng"
        className="flex h-full w-10 items-center justify-center text-foreground-secondary transition-colors hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14" strokeLinecap="round" />
        </svg>
      </button>
      <span className="flex-grow text-center font-body text-lg font-semibold text-foreground">{quantity}</span>
      <button
        type="button"
        onClick={increment}
        disabled={hasMax && quantity >= (max as number)}
        aria-label="Tăng số lượng"
        className="flex h-full w-10 items-center justify-center text-foreground-secondary transition-colors hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}
