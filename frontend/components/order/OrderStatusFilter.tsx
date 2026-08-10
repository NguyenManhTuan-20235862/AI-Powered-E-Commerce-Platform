"use client";

import { useRouter, useSearchParams } from "next/navigation";

import type { OrderStatus } from "@/types/order";

const TABS: { value: OrderStatus | "all"; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "pending", label: "Chờ xác nhận" },
  { value: "confirmed", label: "Đã xác nhận" },
  { value: "shipping", label: "Đang giao" },
  { value: "delivered", label: "Đã giao" },
  { value: "cancelled", label: "Đã hủy" },
];

/**
 * Client Component (task 4.3.3) - tab lọc trạng thái đơn hàng, dùng URL
 * `?status=` làm nguồn sự thật (cùng pattern `ProductFilters`/`SortDropdown`
 * task 4.2.1/4.2.3 - share link/back-forward hoạt động đúng, không phải
 * state cục bộ). `app/(customer)/orders/page.tsx` (Client Component, CSR) tự
 * đọc `useSearchParams()` + refetch khi đổi - component này CHỈ đổi URL,
 * không tự fetch.
 */
export function OrderStatusFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("status") ?? "all";

  function handleSelect(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") params.delete("status");
    else params.set("status", value);
    params.delete("page");
    router.push(`/orders?${params.toString()}`);
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {TABS.map((tab) => (
        <button
          key={tab.value}
          type="button"
          onClick={() => handleSelect(tab.value)}
          aria-pressed={current === tab.value}
          className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
            current === tab.value
              ? "bg-primary text-background"
              : "bg-surface text-foreground-secondary hover:bg-primary-100"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
