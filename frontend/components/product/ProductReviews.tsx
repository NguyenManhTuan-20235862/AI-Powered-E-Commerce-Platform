"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { StarRating } from "@/components/product/StarRating";
import { useAuth } from "@/hooks/useAuth";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Order } from "@/types/order";
import type { Review, ReviewListResponse } from "@/types/review";

const REVIEWS_PAGE_SIZE = 5;
// Max cho phép của PaginationParams Backend (le=100) - đủ cho quy mô đồ án
// (1 customer khó có >100 đơn delivered) - đơn giản hơn hẳn so với tự loop
// nhiều trang chỉ để lọc ra vài đơn chứa đúng sản phẩm này.
const MY_DELIVERED_ORDERS_PAGE_SIZE = 100;

function formatReviewDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/**
 * Thay placeholder tĩnh "Chưa có đánh giá nào" (task "Hoàn thiện review sản
 * phẩm") - Client Component (cần state/fetch/form), đặt trong Server
 * Component `app/(customer)/products/[slug]/page.tsx` cùng cách `ProductInfo`
 * đã tách trước đó.
 *
 * 2 nguồn dữ liệu ĐỘC LẬP, fetch song song:
 * 1. `GET /products/{id}/reviews` - danh sách + điểm trung bình, PUBLIC
 *    (không cần đăng nhập vẫn xem được).
 * 2. `GET /orders?status=delivered` - CHỈ khi đã đăng nhập LÀ Customer, lọc
 *    CỤC BỘ (client-side) những đơn CHỨA đúng sản phẩm này - xác định "đã
 *    mua hàng" + danh sách đơn có thể chọn để gắn review vào (quyết định đã
 *    xác nhận: `order_id` do USER TỰ CHỌN nếu mua ở nhiều đơn khác nhau,
 *    không phải Backend tự đoán) - KHÔNG cần thêm API mới, tái dùng
 *    `GET /orders` đã có.
 */
export function ProductReviews({ productId }: { productId: number }) {
  const { user, isAuthenticated } = useAuth();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [averageRating, setAverageRating] = useState<number | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const fetchReviews = useCallback(async () => {
    setIsLoadingReviews(true);
    setLoadError(false);
    try {
      const { data } = await api.get<ApiResponse<ReviewListResponse>>(`/products/${productId}/reviews`, {
        params: { page, page_size: REVIEWS_PAGE_SIZE },
      });
      setReviews(data.data.items);
      setTotalPages(data.data.total_pages);
      setTotal(data.data.total);
      setAverageRating(data.data.average_rating);
    } catch {
      setLoadError(true);
    } finally {
      setIsLoadingReviews(false);
    }
  }, [productId, page]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  // null = chưa xác định xong (đang tải HOẶC chưa đăng nhập) - phân biệt với
  // [] (đã xác định RÕ user KHÔNG có đơn nào đủ điều kiện) để không hiện
  // nhầm "cần mua hàng" trong lúc vẫn đang chờ API.
  const [eligibleOrders, setEligibleOrders] = useState<Order[] | null>(null);

  const fetchEligibleOrders = useCallback(async () => {
    if (!isAuthenticated || user?.role !== "customer") {
      setEligibleOrders([]);
      return;
    }
    try {
      const { data } = await api.get<ApiResponse<PaginatedResponse<Order>>>("/orders", {
        params: { status: "delivered", page_size: MY_DELIVERED_ORDERS_PAGE_SIZE },
      });
      setEligibleOrders(data.data.items.filter((order) => order.items.some((item) => item.product_id === productId)));
    } catch {
      // Không chặn xem review công khai chỉ vì lỗi kiểm tra "đã mua hàng" -
      // coi như chưa xác định được, ẩn form viết review (an toàn hơn hiện nhầm).
      setEligibleOrders([]);
    }
  }, [isAuthenticated, user, productId]);

  useEffect(() => {
    fetchEligibleOrders();
  }, [fetchEligibleOrders]);

  const [selectedOrderId, setSelectedOrderId] = useState<number | "">("");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Tự chọn sẵn đơn ĐẦU TIÊN khi danh sách đơn hợp lệ vừa có (đỡ phải bấm
  // thêm 1 bước nếu chỉ có đúng 1 đơn) - CHỈ chạy khi chưa chọn gì.
  useEffect(() => {
    if (eligibleOrders && eligibleOrders.length > 0 && selectedOrderId === "") {
      setSelectedOrderId(eligibleOrders[0].id);
    }
  }, [eligibleOrders, selectedOrderId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedOrderId || rating === 0) return;
    setIsSubmitting(true);
    try {
      await api.post(`/products/${productId}/reviews`, {
        order_id: selectedOrderId,
        rating,
        comment: comment.trim() || undefined,
      });
      toast.success("Đánh giá thành công, cảm ơn bạn!");
      setRating(0);
      setComment("");
      // Đơn vừa dùng không còn review lại được nữa (unique index) - loại
      // khỏi danh sách chọn, tránh user bấm gửi lại ngay và nhận lỗi 409.
      setEligibleOrders((prev) => (prev ? prev.filter((o) => o.id !== selectedOrderId) : prev));
      setSelectedOrderId("");
      setPage(1);
      fetchReviews();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Gửi đánh giá thất bại. Vui lòng thử lại."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto mb-16 max-w-3xl">
      <h2 className="mb-6 text-center font-heading text-2xl text-foreground">Đánh giá sản phẩm</h2>

      {!isLoadingReviews && total > 0 && (
        <div className="mb-8 flex flex-col items-center gap-2 rounded-2xl bg-surface/30 p-6 text-center shadow-soft">
          <span className="font-heading text-4xl text-foreground">{averageRating?.toFixed(1)}</span>
          <StarRating value={averageRating ?? 0} />
          <p className="text-sm text-foreground-muted">{total} đánh giá</p>
        </div>
      )}

      {isAuthenticated && user?.role === "customer" && (
        <div className="mb-8 rounded-2xl border border-border bg-background p-6">
          {eligibleOrders === null ? (
            <p className="text-sm text-foreground-muted">Đang kiểm tra...</p>
          ) : eligibleOrders.length === 0 ? (
            <p className="text-sm text-foreground-muted">
              Bạn cần mua và nhận hàng sản phẩm này trước khi có thể đánh giá.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <h3 className="font-heading text-lg text-foreground">Viết đánh giá của bạn</h3>

              {eligibleOrders.length > 1 && (
                <div className="flex flex-col gap-1">
                  <label htmlFor="review-order" className="text-sm font-semibold text-foreground-secondary">
                    Chọn đơn hàng
                  </label>
                  <select
                    id="review-order"
                    value={selectedOrderId}
                    onChange={(e) => setSelectedOrderId(Number(e.target.value))}
                    className="rounded-lg border border-border bg-background px-4 py-2 text-sm outline-none focus:border-primary"
                  >
                    {eligibleOrders.map((order) => (
                      <option key={order.id} value={order.id}>
                        Đơn #{order.id} - {formatReviewDate(order.created_at)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold text-foreground-secondary">Số sao</span>
                <StarRating value={rating} onChange={setRating} size={28} />
              </div>

              <div className="flex flex-col gap-1">
                <label htmlFor="review-comment" className="text-sm font-semibold text-foreground-secondary">
                  Nhận xét (không bắt buộc)
                </label>
                <textarea
                  id="review-comment"
                  rows={3}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="resize-none rounded-lg border border-border bg-background px-4 py-3 text-sm outline-none focus:border-primary"
                  placeholder="Chia sẻ cảm nhận của bạn về sản phẩm..."
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || rating === 0}
                className="self-start rounded-full bg-primary px-6 py-2 font-heading text-sm text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Đang gửi..." : "Gửi đánh giá"}
              </button>
            </form>
          )}
        </div>
      )}

      {!isAuthenticated && (
        <p className="mb-8 text-center text-sm text-foreground-muted">
          <Link href="/login" className="font-semibold text-primary hover:underline">
            Đăng nhập
          </Link>{" "}
          để viết đánh giá cho sản phẩm này.
        </p>
      )}

      {isLoadingReviews ? (
        <p className="text-center text-foreground-muted">Đang tải đánh giá...</p>
      ) : loadError ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-error">Không thể tải đánh giá. Vui lòng thử lại.</p>
          <button
            type="button"
            onClick={fetchReviews}
            className="rounded-full bg-primary px-6 py-2 font-heading text-sm text-background hover:bg-primary-hover"
          >
            Thử lại
          </button>
        </div>
      ) : reviews.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-3xl bg-surface/30 py-16 text-center shadow-soft">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-surface text-foreground-muted">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4h16v12H8l-4 4V4Z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <p className="text-lg text-foreground-secondary">Chưa có đánh giá nào.</p>
          <p className="max-w-sm text-sm text-foreground-secondary opacity-80">
            Hãy là người đầu tiên chia sẻ cảm nhận về sản phẩm này với cộng đồng Vun.
          </p>
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-border">
          {reviews.map((review) => (
            <div key={review.id} className="py-5">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground">{review.user_name}</span>
                <span className="text-xs text-foreground-muted">{formatReviewDate(review.created_at)}</span>
              </div>
              <div className="mb-2 flex items-center gap-2">
                <StarRating value={review.rating} size={16} />
                {review.is_verified_purchase && (
                  <span className="rounded-full bg-secondary-100 px-2 py-0.5 text-xs font-semibold text-secondary-800">
                    Đã mua hàng
                  </span>
                )}
              </div>
              {review.comment && <p className="text-sm text-foreground-secondary">{review.comment}</p>}
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => setPage((p) => p - 1)}
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
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          >
            Trang sau
          </button>
        </div>
      )}
    </section>
  );
}
