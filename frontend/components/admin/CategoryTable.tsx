"use client";

import { useState } from "react";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import type { Category } from "@/types/category";

const DESCRIPTION_TRUNCATE_LENGTH = 60;

function truncate(text: string | null, length: number): string {
  if (!text) return "—";
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

/**
 * Client Component (CRUD Category Admin) - bảng danh mục, HTML `<table>`
 * thuần (cùng quyết định `ProductTable.tsx`/`UserTable.tsx`). KHÔNG có ô
 * search/filter/phân trang - `GET /categories` không hỗ trợ (trả TOÀN BỘ
 * danh mục 1 lần, không phân trang - số lượng danh mục nhỏ, xem
 * `category_service.list_categories()`), xây UI filter cho thứ Backend
 * không hỗ trợ không tương xứng.
 *
 * KHÔNG có cột "số sản phẩm thuộc về nó" - `CategoryRead` không trả field
 * này, gọi thêm API riêng chỉ để đếm cho 1 cột không thiết yếu không tương
 * xứng ở quy mô đồ án (đã xác nhận trước khi code - bỏ qua cột này cho đơn
 * giản).
 *
 * "Danh mục cha" hiển thị TÊN (tra qua `categoryById`, map dựng từ chính
 * danh sách `categories` đã có sẵn - không cần round-trip API riêng), không
 * phải `parent_id` số trơ.
 */
export function CategoryTable({
  categories,
  isLoading,
  onEdit,
  onChanged,
}: {
  categories: Category[];
  isLoading: boolean;
  onEdit: (category: Category) => void;
  onChanged: () => void;
}) {
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const categoryById = new Map(categories.map((c) => [c.id, c]));

  async function handleDelete(category: Category) {
    const confirmed = window.confirm(`Xác nhận xóa danh mục "${category.name}"?`);
    if (!confirmed) return;

    setDeletingId(category.id);
    try {
      await api.delete(`/categories/${category.id}`);
      toast.success("Đã xóa danh mục");
      onChanged();
    } catch (err) {
      // extractApiErrorMessage đọc thẳng message thật từ Backend (VD "Không
      // thể xóa danh mục còn 20 sản phẩm"/"...còn 1 danh mục con") - KHÔNG
      // hiện thông báo lỗi generic cho case 409 này, Admin cần biết CHÍNH
      // XÁC lý do để xử lý đúng hướng (xóa sản phẩm/danh mục con trước).
      toast.error(extractApiErrorMessage(err, "Xóa danh mục thất bại. Vui lòng thử lại."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-border bg-background">
            <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Tên danh mục</th>
            <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Slug</th>
            <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Mô tả</th>
            <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Danh mục cha</th>
            <th className="w-24 px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Hành động</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {isLoading ? (
            <tr>
              <td colSpan={5} className="px-4 py-10 text-center text-foreground-muted">
                Đang tải...
              </td>
            </tr>
          ) : categories.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-10 text-center text-foreground-muted">
                Chưa có danh mục nào.
              </td>
            </tr>
          ) : (
            categories.map((category) => {
              const parent = category.parent_id ? categoryById.get(category.parent_id) : undefined;
              return (
                <tr key={category.id} className="hover:bg-primary-100/40">
                  <td className="px-4 py-2 text-sm font-medium text-foreground">{category.name}</td>
                  <td className="px-4 py-2 text-sm text-foreground-muted">{category.slug}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">
                    {truncate(category.description, DESCRIPTION_TRUNCATE_LENGTH)}
                  </td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{parent ? parent.name : "—"}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => onEdit(category)}
                        title="Sửa"
                        className="rounded p-1 text-foreground-muted hover:bg-primary-100 hover:text-primary"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                          <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(category)}
                        disabled={deletingId === category.id}
                        title="Xóa"
                        className="rounded p-1 text-foreground-muted hover:bg-error-container hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                          <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6h16Z" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      {/* Không có "Hiển thị X-Y trên tổng Z" như Product/OrderTable - GET
          /categories không phân trang thật (trả toàn bộ 1 lần), X-Y vô nghĩa
          khi luôn hiện đủ trong 1 "trang" - chỉ hiện tổng số. */}
      {!isLoading && categories.length > 0 && (
        <div className="border-t border-border px-4 py-3">
          <span className="text-sm text-foreground-muted">Tổng {categories.length} danh mục</span>
        </div>
      )}
    </div>
  );
}
