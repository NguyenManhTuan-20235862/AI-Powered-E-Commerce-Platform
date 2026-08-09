"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { Category } from "@/types/category";

/**
 * Client Component - cần state cho checkbox/input/toggle tương tác.
 *
 * Danh mục: Backend (`GET /products`) chỉ nhận 1 `category_id` (không phải
 * mảng) - checkbox ở đây cố tình hoạt động KIỂU RADIO (chọn 1 mục sẽ bỏ chọn
 * mục còn lại) dù hiển thị bằng checkbox (giữ đúng UI Stitch đã thiết kế),
 * KHÔNG hỗ trợ chọn nhiều danh mục cùng lúc.
 */
export function ProductFilters({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [categoryId, setCategoryId] = useState(searchParams.get("category") ?? "");
  const [minPrice, setMinPrice] = useState(searchParams.get("min_price") ?? "");
  const [maxPrice, setMaxPrice] = useState(searchParams.get("max_price") ?? "");
  const [inStock, setInStock] = useState(searchParams.get("in_stock") === "1");
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  function applyFilters() {
    const params = new URLSearchParams(searchParams.toString());
    if (categoryId) params.set("category", categoryId);
    else params.delete("category");
    if (minPrice) params.set("min_price", minPrice);
    else params.delete("min_price");
    if (maxPrice) params.set("max_price", maxPrice);
    else params.delete("max_price");
    if (inStock) params.set("in_stock", "1");
    else params.delete("in_stock");
    // Đổi filter -> luôn quay về trang 1 (trang N cũ có thể không còn tồn
    // tại với tập kết quả mới, nhỏ hơn).
    params.delete("page");
    setIsMobileOpen(false);
    router.push(`/products?${params.toString()}`);
  }

  const formContent = (
    <>
      <div>
        <h2 className="mb-1 font-heading text-xl text-primary">Bộ lọc</h2>
        <p className="text-sm text-foreground-muted">Tìm kiếm sản phẩm</p>
      </div>
      <hr className="border-t border-border" />

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Danh mục</h3>
        <div className="flex flex-col gap-2 pl-1">
          {categories.length === 0 ? (
            <p className="text-sm text-foreground-muted">Chưa có danh mục nào.</p>
          ) : (
            categories.map((category) => (
              <label key={category.id} className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  checked={categoryId === String(category.id)}
                  onChange={() =>
                    setCategoryId((current) => (current === String(category.id) ? "" : String(category.id)))
                  }
                />
                <span className="text-foreground-secondary">{category.name}</span>
              </label>
            ))
          )}
        </div>
      </div>
      <hr className="border-t border-border" />

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Khoảng giá</h3>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            placeholder="Từ"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
          />
          <span className="text-foreground-muted">-</span>
          <input
            type="number"
            min={0}
            placeholder="Đến"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <hr className="border-t border-border" />

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Trạng thái</h3>
        <label className="flex cursor-pointer items-center justify-between">
          <span className="text-foreground-secondary">Còn hàng</span>
          <button
            type="button"
            role="switch"
            aria-checked={inStock}
            onClick={() => setInStock((v) => !v)}
            className={`relative h-6 w-11 rounded-full transition-colors ${inStock ? "bg-primary" : "bg-background"}`}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                inStock ? "translate-x-[22px]" : "translate-x-0.5"
              }`}
            />
          </button>
        </label>
      </div>

      <button
        type="button"
        onClick={applyFilters}
        className="w-full rounded-md bg-primary-100 py-3 font-heading text-sm text-primary-800 transition-colors hover:bg-primary-300"
      >
        Áp dụng
      </button>
    </>
  );

  return (
    <>
      <div className="flex items-center justify-between rounded-lg bg-surface p-3 md:hidden">
        <span className="font-heading text-foreground">Bộ lọc</span>
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          className="rounded-full bg-primary-100 px-4 py-1.5 text-sm text-primary-800"
        >
          Mở bộ lọc
        </button>
      </div>

      {isMobileOpen && (
        <div className="fixed inset-0 z-40 bg-foreground/40 md:hidden" onClick={() => setIsMobileOpen(false)} />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-72 flex-col gap-4 overflow-y-auto bg-surface p-4 transition-transform duration-200 ease-in-out md:static md:z-auto md:h-fit md:w-1/4 md:translate-x-0 md:rounded-2xl md:shadow-sm ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {formContent}
      </aside>
    </>
  );
}
