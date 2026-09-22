"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { ReviewTable } from "@/components/admin/ReviewTable";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { AdminReview } from "@/types/review";

/**
 * Trang moderation review (task "Hoàn thiện review sản phẩm" - mở rộng,
 * KHÔNG có trong `docs/API_SPEC.md` bản gốc, xem quyết định đã xác nhận).
 * CSR + state `useState` thường (KHÔNG đồng bộ qua URL `searchParams`) -
 * cùng quyết định đã áp dụng cho `/admin/users`/`/admin/orders`.
 */
export default function AdminReviewsPage() {
  const [reviews, setReviews] = useState<AdminReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [isDeleted, setIsDeleted] = useState<"" | "true" | "false">("");

  const fetchReviews = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (isDeleted) params.is_deleted = isDeleted;
      const { data } = await api.get<ApiResponse<PaginatedResponse<AdminReview>>>("/reviews", { params });
      setReviews(data.data.items);
      setTotalPages(data.data.total_pages);
      setTotal(data.data.total);
      setPageSize(data.data.page_size);
    } catch {
      toast.error("Không tải được danh sách đánh giá.");
    } finally {
      setIsLoading(false);
    }
  }, [page, isDeleted]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  function handleStatusChange(value: "" | "true" | "false") {
    setIsDeleted(value);
    setPage(1);
  }

  // Patch ĐÚNG 1 dòng trong state cục bộ - KHÔNG gọi lại fetchReviews()
  // (toàn bảng), cùng quyết định đã áp dụng cho khóa/mở khóa user
  // (UserTable.tsx/AdminUsersPage) - kết quả soft-delete luôn xác định
  // (thành công = is_deleted true), không cần đọc lại từ API.
  function handleDeleted(reviewId: string) {
    setReviews((prev) => prev.map((r) => (r.id === reviewId ? { ...r, is_deleted: true } : r)));
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl text-foreground">Quản lý đánh giá</h1>
        <p className="mt-1 text-sm text-foreground-muted">Xem và xóa đánh giá vi phạm.</p>
      </div>

      <ReviewTable
        reviews={reviews}
        isLoading={isLoading}
        isDeleted={isDeleted}
        onStatusChange={handleStatusChange}
        page={page}
        totalPages={totalPages}
        total={total}
        pageSize={pageSize}
        onPageChange={setPage}
        onDeleted={handleDeleted}
      />
    </div>
  );
}
