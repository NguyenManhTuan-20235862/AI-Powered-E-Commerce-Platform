"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import type { ProductSortBy } from "@/types/product";

const SORT_OPTIONS: { value: ProductSortBy; label: string }[] = [
  { value: "newest", label: "Mới nhất" },
  { value: "price_asc", label: "Giá thấp đến cao" },
  { value: "price_desc", label: "Giá cao đến thấp" },
];

export function SortDropdown() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const currentSort = (searchParams.get("sort_by") as ProductSortBy | null) ?? "newest";

  function handleChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "newest") params.delete("sort_by");
    else params.set("sort_by", value);
    params.delete("page");
    startTransition(() => {
      router.push(`/products?${params.toString()}`);
    });
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="sort_by" className="text-sm text-foreground-secondary">
        Sắp xếp:
      </label>
      <select
        id="sort_by"
        value={currentSort}
        onChange={(e) => handleChange(e.target.value)}
        disabled={isPending}
        className="cursor-pointer rounded-md border border-border bg-background py-1.5 pl-3 pr-8 text-sm text-foreground focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {isPending && (
        <span
          aria-label="Đang cập nhật kết quả"
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-100 border-t-primary"
        />
      )}
    </div>
  );
}
