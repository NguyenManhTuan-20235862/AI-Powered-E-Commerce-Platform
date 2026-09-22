"use client";

import { useState } from "react";
import { toast } from "sonner";

import { StarRating } from "@/components/product/StarRating";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPaginationRange } from "@/lib/format";
import type { AdminReview } from "@/types/review";

const STATUS_FILTER_OPTIONS: { value: "" | "true" | "false"; label: string }[] = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "false", label: "Đang hiển thị" },
  { value: "true", label: "Đã xóa" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/**
 * Bảng moderation review (task "Hoàn thiện review sản phẩm" - mở rộng, xem
 * quyết định đã xác nhận: xây thêm `GET /reviews` Admin + trang này dù
 * `docs/API_SPEC.md` bản gốc chỉ có `DELETE /reviews/{id}`).
 *
 * KHÁC `UserTable.tsx`/`CategoryTable.tsx`: KHÔNG ẩn dòng đã xóa - Admin cần
 * thấy CẢ review đã xóa mềm (đúng mục đích "audit trail" của thiết kế
 * soft-delete) - dòng đã xóa vẫn hiện (mờ đi qua `opacity-60`), chỉ ẩn nút
 * "Xóa" (không xóa lại được review đã xóa - khớp đúng `soft_delete_review()`
 * Backend, gọi lại trả 404).
 *
 * Xóa xong KHÔNG gọi lại API list toàn bộ - `onDeleted(review.id)` báo cha
 * (`page.tsx`) tự patch `is_deleted: true` cho ĐÚNG 1 dòng trong state cục
 * bộ (kết quả xóa mềm luôn xác định: thành công = is_deleted true, không
 * cần đọc lại response `DELETE` - endpoint đó vốn không trả lại document).
 */
export function ReviewTable({
  reviews,
  isLoading,
  isDeleted,
  onStatusChange,
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  onDeleted,
}: {
  reviews: AdminReview[];
  isLoading: boolean;
  isDeleted: "" | "true" | "false";
  onStatusChange: (value: "" | "true" | "false") => void;
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onDeleted: (reviewId: string) => void;
}) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { start, end } = formatPaginationRange(page, pageSize, total);

  async function handleDelete(review: AdminReview) {
    const confirmed = window.confirm(
      `Xác nhận xóa đánh giá của "${review.user_name}" cho sản phẩm "${review.product_name ?? `#${review.product_id}`}"? Hành động này sẽ ẩn đánh giá khỏi trang sản phẩm.`,
    );
    if (!confirmed) return;

    setDeletingId(review.id);
    try {
      await api.delete(`/reviews/${review.id}`);
      toast.success("Đã xóa đánh giá");
      onDeleted(review.id);
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Xóa đánh giá thất bại. Vui lòng thử lại."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end rounded-xl border border-border bg-surface p-4">
        <select
          value={isDeleted}
          onChange={(e) => onStatusChange(e.target.value as "" | "true" | "false")}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary sm:w-48"
        >
          {STATUS_FILTER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border bg-background">
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Sản phẩm</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Người đánh giá</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Số sao</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Nhận xét</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Ngày</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Trạng thái</th>
              <th className="w-32 px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Đang tải...
                </td>
              </tr>
            ) : reviews.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Không có đánh giá nào khớp bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              reviews.map((review) => (
                <tr key={review.id} className={`hover:bg-primary-100/40 ${review.is_deleted ? "opacity-60" : ""}`}>
                  <td className="px-4 py-2 text-sm text-foreground">{review.product_name ?? `#${review.product_id}`}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{review.user_name}</td>
                  <td className="px-4 py-2">
                    <StarRating value={review.rating} size={14} />
                  </td>
                  <td className="max-w-xs truncate px-4 py-2 text-sm text-foreground-secondary">{review.comment ?? "—"}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{formatDate(review.created_at)}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        review.is_deleted ? "bg-error-container text-error" : "bg-secondary-100 text-secondary-800"
                      }`}
                    >
                      {review.is_deleted ? "Đã xóa" : "Đang hiển thị"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {review.is_deleted ? (
                      <span className="text-foreground-muted">—</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleDelete(review)}
                        disabled={deletingId === review.id}
                        className="rounded border border-foreground-muted px-4 py-1.5 text-sm text-foreground-secondary transition-colors hover:border-error hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {deletingId === review.id ? "..." : "Xóa"}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {!isLoading && reviews.length > 0 && (
          <div className="flex flex-col items-center justify-between gap-2 border-t border-border px-4 py-3 sm:flex-row">
            <span className="text-sm text-foreground-muted">
              Hiển thị {start}-{end} trên tổng {total} đánh giá
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
