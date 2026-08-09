"use client";

/**
 * Client Component - +/- số lượng. Component ĐIỀU KHIỂN (controlled, task
 * 4.3.1 - trước đó tự giữ state nội bộ, CHƯA nối giỏ hàng thật): cha
 * (`AddToCartSection`) giữ `quantity`, truyền xuống qua props cùng `onChange`
 * - cần vậy vì cha phải biết quantity hiện tại lúc gọi `addItem()`.
 */
export function QuantitySelector({
  quantity,
  onChange,
  max,
}: {
  quantity: number;
  onChange: (quantity: number) => void;
  max?: number;
}) {
  const hasMax = typeof max === "number" && max > 0;

  function decrement() {
    onChange(Math.max(1, quantity - 1));
  }

  function increment() {
    onChange(hasMax ? Math.min(max as number, quantity + 1) : quantity + 1);
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
