"use client";

import { useState } from "react";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPaginationRange, formatPriceVnd, resolveProductImageUrlClient } from "@/lib/format";
import type { Category } from "@/types/category";
import type { Product } from "@/types/product";

/**
 * Client Component (task 4.4.1) - bảng danh sách sản phẩm Admin, dùng HTML
 * `<table>` thuần (KHÔNG thêm thư viện table nào - TanStack Table giải quyết
 * virtualization/sort đa cột/resize cột phức tạp mà quy mô đồ án (bảng
 * server-paginate, sort đơn giản theo id, search + filter category cơ bản)
 * không cần tới - thêm dependency mới cho lợi ích không đáng kể không khớp
 * triết lý "quy mô đồ án" đã dùng xuyên suốt dự án, VD Cart/Order dùng div
 * thuần thay vì grid library).
 *
 * Toggle "Ẩn"/"Hiện" mỗi dòng tự quản `isTogglingId` cục bộ, gọi thẳng
 * `PUT /products/{id}` với `{is_active}` (KHÔNG dùng `DELETE` - xem giải
 * thích lúc audit: DELETE chỉ 1 chiều tắt, PUT mới bật lại được, dùng PUT
 * cho CẢ 2 chiều để nhất quán 1 cơ chế duy nhất).
 */
export function ProductTable({
  products,
  isLoading,
  search,
  onSearchChange,
  categoryId,
  onCategoryChange,
  categories,
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  onEdit,
  onChanged,
}: {
  products: Product[];
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  categoryId: string;
  onCategoryChange: (value: string) => void;
  categories: Category[];
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onEdit: (product: Product) => void;
  onChanged: () => void;
}) {
  const { start, end } = formatPaginationRange(page, pageSize, total);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  async function handleToggleActive(product: Product) {
    setTogglingId(product.id);
    try {
      await api.put(`/products/${product.id}`, { is_active: !product.is_active });
      toast.success(product.is_active ? "Đã ẩn sản phẩm" : "Đã hiện sản phẩm");
      onChanged();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Cập nhật trạng thái thất bại. Vui lòng thử lại."));
    } finally {
      setTogglingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col items-center justify-between gap-3 rounded-xl border border-border bg-surface p-4 sm:flex-row">
        <div className="relative w-full sm:w-96">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm kiếm theo tên sản phẩm..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-primary"
          />
        </div>
        <select
          value={categoryId}
          onChange={(e) => onCategoryChange(e.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary sm:w-48"
        >
          <option value="">Tất cả danh mục</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border bg-background">
              <th className="w-16 px-4 py-3 text-xs font-semibold text-foreground-secondary">Ảnh</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Tên sản phẩm</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Danh mục</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Giá</th>
              <th className="w-24 px-4 py-3 text-center text-xs font-semibold text-foreground-secondary">Tồn kho</th>
              <th className="w-32 px-4 py-3 text-xs font-semibold text-foreground-secondary">Trạng thái</th>
              <th className="w-24 px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Đang tải...
                </td>
              </tr>
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Không có sản phẩm nào khớp bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              products.map((product) => {
                const imageUrl = resolveProductImageUrlClient(product.image_url);
                return (
                  <tr key={product.id} className="group hover:bg-primary-100/40">
                    <td className="px-4 py-2">
                      <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded bg-background">
                        {imageUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={imageUrl} alt={product.name} className="h-full w-full object-cover" />
                        ) : (
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-foreground-muted">
                            <rect x="3" y="3" width="18" height="18" rx="2" />
                            <circle cx="9" cy="9" r="2" />
                          </svg>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm font-medium text-foreground">{product.name}</td>
                    <td className="px-4 py-2 text-sm text-foreground-secondary">{product.category.name}</td>
                    <td className="px-4 py-2 text-right text-sm font-semibold text-primary">
                      {formatPriceVnd(product.price)}
                    </td>
                    <td className="px-4 py-2 text-center text-sm text-foreground-secondary">
                      {product.stock_quantity}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-1 text-[12px] font-semibold ${
                          product.is_active ? "bg-secondary-100 text-secondary-800" : "bg-error-container text-error"
                        }`}
                      >
                        {product.is_active ? "Đang bán" : "Đã ẩn"}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onEdit(product)}
                          title="Sửa"
                          className="rounded p-1 text-foreground-muted hover:bg-primary-100 hover:text-primary"
                        >
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                            <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleActive(product)}
                          disabled={togglingId === product.id}
                          title={product.is_active ? "Ẩn" : "Hiện"}
                          className="rounded p-1 text-foreground-muted hover:bg-primary-100 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {product.is_active ? (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" strokeLinecap="round" strokeLinejoin="round" />
                              <circle cx="12" cy="12" r="3" />
                              <path d="M4 20 20 4" strokeLinecap="round" />
                            </svg>
                          ) : (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" strokeLinecap="round" strokeLinejoin="round" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {!isLoading && products.length > 0 && (
          <div className="flex flex-col items-center justify-between gap-2 border-t border-border px-4 py-3 sm:flex-row">
            <span className="text-sm text-foreground-muted">
              Hiển thị {start}-{end} trên tổng {total} sản phẩm
            </span>
            {totalPages > 1 && (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => onPageChange(page - 1)}
                  disabled={page <= 1}
                  className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Trang trước
                </button>
                <span className="text-sm text-foreground-muted">
                  Trang {page}/{totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => onPageChange(page + 1)}
                  disabled={page >= totalPages}
                  className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Trang sau
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
