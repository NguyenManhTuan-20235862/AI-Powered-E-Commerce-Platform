"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import type { Category } from "@/types/category";

// task 4.2.3 - debounce cho search: chờ người dùng ngừng gõ mới điều hướng,
// tránh gọi API mỗi phím gõ.
const SEARCH_DEBOUNCE_MS = 450;

/**
 * Client Component - cần state cho checkbox/input/toggle/search tương tác.
 *
 * Danh mục: Backend (`GET /products`) chỉ nhận 1 `category_id` (không phải
 * mảng) - checkbox ở đây cố tình hoạt động KIỂU RADIO (chọn 1 mục sẽ bỏ chọn
 * mục còn lại) dù hiển thị bằng checkbox (giữ đúng UI Stitch đã thiết kế),
 * KHÔNG hỗ trợ chọn nhiều danh mục cùng lúc.
 *
 * Đồng bộ URL -> widget (task 4.2.3, sửa bug thật đã có từ 4.2.1): state của
 * các input này ban đầu chỉ đọc `searchParams` MỘT LẦN lúc mount (qua
 * `useState` initializer) - khi URL đổi từ BÊN NGOÀI component (nút back/
 * forward trình duyệt, hoặc SortDropdown điều hướng) mà KHÔNG qua nút
 * "Áp dụng" ở đây, danh sách sản phẩm vẫn đúng (Server Component luôn
 * re-render theo URL thật) nhưng checkbox/input HIỂN THỊ SAI (state cũ, không
 * tự cập nhật). `useEffect` bên dưới resync lại toàn bộ state theo
 * `searchParams` mỗi khi nó đổi (kể cả đổi từ bên ngoài) - bắt buộc phải có,
 * KHÔNG thể chỉ dựa vào initializer của `useState`.
 *
 * Loading state (task 4.2.3): dùng `useTransition` (spinner cục bộ ở nút
 * "Áp dụng"), KHÔNG dùng `app/(customer)/products/loading.tsx` (Next.js
 * Suspense boundary tự động) - đã tự thử, gặp bug thật: Server trả response
 * đầy đủ rất nhanh (~500ms, xác nhận qua log + curl nhận đúng toàn bộ nội
 * dung), nhưng trình duyệt treo VĨNH VIỄN ở skeleton, không bao giờ swap
 * sang nội dung thật (tái hiện được nhiều lần, kể cả sau khi restart dev
 * server) - gỡ bỏ `loading.tsx`, không điều tra sâu hơn (không đáng thời
 * gian cho 1 file loading tĩnh), chuyển hẳn sang `useTransition` cho chắc.
 */
export function ProductFilters({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [categoryId, setCategoryId] = useState(searchParams.get("category") ?? "");
  const [minPrice, setMinPrice] = useState(searchParams.get("min_price") ?? "");
  const [maxPrice, setMaxPrice] = useState(searchParams.get("max_price") ?? "");
  const [inStock, setInStock] = useState(searchParams.get("in_stock") === "1");
  const [searchTerm, setSearchTerm] = useState(searchParams.get("search") ?? "");
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    setCategoryId(searchParams.get("category") ?? "");
    setMinPrice(searchParams.get("min_price") ?? "");
    setMaxPrice(searchParams.get("max_price") ?? "");
    setInStock(searchParams.get("in_stock") === "1");
    setSearchTerm(searchParams.get("search") ?? "");
  }, [searchParams]);

  // Debounce search - CHỈ điều hướng khi searchTerm THẬT SỰ khác giá trị
  // đang có trên URL (tránh tự bắn thêm 1 lượt điều hướng thừa ngay sau khi
  // effect resync ở trên vừa set lại searchTerm về đúng giá trị URL).
  useEffect(() => {
    const timer = setTimeout(() => {
      const currentSearch = searchParams.get("search") ?? "";
      if (searchTerm === currentSearch) return;
      const params = new URLSearchParams(searchParams.toString());
      if (searchTerm) params.set("search", searchTerm);
      else params.delete("search");
      params.delete("page");
      startTransition(() => {
        router.push(`/products?${params.toString()}`);
      });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchTerm, searchParams, router]);

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
    startTransition(() => {
      router.push(`/products?${params.toString()}`);
    });
  }

  function resetFilters() {
    setCategoryId("");
    setMinPrice("");
    setMaxPrice("");
    setInStock(false);
    setSearchTerm("");
    setIsMobileOpen(false);
    startTransition(() => {
      router.push("/products");
    });
  }

  const hasActiveFilters = Boolean(categoryId || minPrice || maxPrice || inStock || searchTerm);

  const formContent = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="mb-1 flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-heading text-xl text-primary">
              Bộ lọc
              {isPending && (
                <span
                  aria-label="Đang cập nhật kết quả"
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-100 border-t-primary"
                />
              )}
            </h2>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                disabled={isPending}
                className="text-xs text-foreground-secondary underline hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                Xóa bộ lọc
              </button>
            )}
          </div>
          <p className="text-sm text-foreground-muted">Tìm kiếm sản phẩm</p>
        </div>
        <button
          type="button"
          onClick={() => setIsMobileOpen(false)}
          aria-label="Đóng bộ lọc"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-foreground-secondary hover:bg-primary-100 hover:text-foreground md:hidden"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div className="relative">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.3-4.3" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Tên sản phẩm..."
          aria-label="Tìm kiếm sản phẩm theo tên"
          className="w-full rounded-md border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground focus:border-primary focus:outline-none"
        />
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
              className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                inStock ? "translate-x-[22px]" : "translate-x-0"
              }`}
            />
          </button>
        </label>
      </div>

      <button
        type="button"
        onClick={applyFilters}
        disabled={isPending}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-primary-100 py-3 font-heading text-sm text-primary-800 transition-colors hover:bg-primary-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-300 border-t-primary-800" />}
        {isPending ? "Đang áp dụng..." : "Áp dụng"}
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
        // bg-black/40 (KHÔNG PHẢI bg-foreground/40) - foreground là CSS custom
        // property trần (var(--color-text), app/globals.css), Tailwind không
        // tạo được utility opacity cho màu dạng này (đã tự kiểm chứng: build
        // ra .bg-foreground nhưng KHÔNG có .bg-foreground\/40 nào cả -> lớp
        // phủ vô hình, backdrop không tối đi). Màu built-in (black) hỗ trợ
        // opacity modifier bình thường.
        <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setIsMobileOpen(false)} />
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
