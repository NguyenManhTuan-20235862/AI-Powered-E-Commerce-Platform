"use client";

import { useCallback, useEffect, useState } from "react";

import { OrderStatusBadge } from "@/components/order/OrderStatusBadge";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Order } from "@/types/order";
import type { AdminUser } from "@/types/user";

const ORDERS_PAGE_SIZE = 5;

type LoadState = "loading" | "ready" | "error";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Modal chi tiết 1 user + lịch sử đơn hàng (task "Hoàn thiện quản lý tài
 * khoản Admin") - cùng vỏ dialog `InventoryAdjustmentModal.tsx`
 * (`fixed inset-0 ... bg-black/40` + `role="dialog"`), KHÔNG dùng route
 * riêng (`/admin/users/[id]`) - Admin panel chưa có tiền lệ route chi tiết
 * nào (Product/Category đều sửa qua modal), thêm 1 route mới chỉ cho 1 view
 * (không sửa được gì) không tương xứng.
 *
 * Fetch LẠI `GET /users/{id}` khi mở (KHÔNG tin dữ liệu dòng bảng đang có) -
 * cho dữ liệu mới nhất + cho endpoint này (trước đó Frontend hoàn toàn
 * không gọi, dù đã có sẵn ở Backend/API_SPEC.md) một mục đích sử dụng thật.
 * Lịch sử đơn gọi `GET /orders/admin?user_id=<id>` (tham số mới thêm cùng
 * task này, `order_service.list_orders()` vốn đã hỗ trợ sẵn `user_id`,
 * trước đó chỉ Customer dùng qua `GET /orders`).
 */
export function UserDetailModal({ userId, onClose }: { userId: number; onClose: () => void }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [userLoadState, setUserLoadState] = useState<LoadState>("loading");
  const [userError, setUserError] = useState<string | null>(null);

  const [orders, setOrders] = useState<Order[]>([]);
  const [ordersPage, setOrdersPage] = useState(1);
  const [ordersTotalPages, setOrdersTotalPages] = useState(1);
  const [ordersLoadState, setOrdersLoadState] = useState<LoadState>("loading");

  const fetchUser = useCallback(async () => {
    setUserLoadState("loading");
    try {
      const { data } = await api.get<ApiResponse<AdminUser>>(`/users/${userId}`);
      setUser(data.data);
      setUserLoadState("ready");
    } catch (err) {
      setUserError(extractApiErrorMessage(err, "Không thể tải thông tin người dùng."));
      setUserLoadState("error");
    }
  }, [userId]);

  const fetchOrders = useCallback(async () => {
    setOrdersLoadState("loading");
    try {
      const { data } = await api.get<ApiResponse<PaginatedResponse<Order>>>("/orders/admin", {
        params: { user_id: userId, page: ordersPage, page_size: ORDERS_PAGE_SIZE },
      });
      setOrders(data.data.items);
      setOrdersTotalPages(data.data.total_pages);
      setOrdersLoadState("ready");
    } catch {
      setOrdersLoadState("error");
    }
  }, [userId, ordersPage]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  return (
    // Bấm nền tối đóng modal (KHÔNG có trong InventoryAdjustmentModal vì đó là
    // form nhập liệu, lỡ tay bấm ngoài mất dữ liệu đang nhập - modal này CHỈ
    // xem, không có gì để mất) - stopPropagation() ở card bên trong để bấm
    // trong modal không tính là bấm nền.
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-detail-title"
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[85vh] w-full max-w-2xl flex-col gap-4 overflow-y-auto rounded-2xl bg-surface p-6 shadow-warm"
      >
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h2 id="user-detail-title" className="font-heading text-xl text-foreground">
            Chi tiết người dùng
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="rounded p-1 text-foreground-muted hover:bg-primary-100 hover:text-foreground"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {userLoadState === "loading" && <p className="text-foreground-muted">Đang tải...</p>}
        {userLoadState === "error" && (
          <p role="alert" className="text-error">
            {userError}
          </p>
        )}
        {userLoadState === "ready" && user && (
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-foreground-muted">Họ tên</dt>
              <dd className="text-foreground">{user.full_name}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Email</dt>
              <dd className="text-foreground">{user.email}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Số điện thoại</dt>
              <dd className="text-foreground">{user.phone ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Vai trò</dt>
              <dd className="text-foreground">{user.role === "admin" ? "Admin" : "Customer"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-foreground-muted">Địa chỉ</dt>
              <dd className="text-foreground">{user.address ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Trạng thái</dt>
              <dd className="text-foreground">{user.is_active ? "Đang hoạt động" : "Đã khóa"}</dd>
            </div>
            <div>
              <dt className="text-foreground-muted">Ngày tham gia</dt>
              <dd className="text-foreground">{formatDateTime(user.created_at)}</dd>
            </div>
          </dl>
        )}

        <div className="border-t border-border pt-4">
          <h3 className="mb-3 font-heading text-lg text-primary">Lịch sử đơn hàng</h3>
          {ordersLoadState === "loading" ? (
            <p className="text-foreground-muted">Đang tải...</p>
          ) : ordersLoadState === "error" ? (
            <p role="alert" className="text-error">
              Không thể tải lịch sử đơn hàng.
            </p>
          ) : orders.length === 0 ? (
            <p className="text-foreground-muted">Người dùng chưa có đơn hàng nào.</p>
          ) : (
            <>
              <div className="flex flex-col divide-y divide-border">
                {orders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">#{order.id}</p>
                      <p className="text-xs text-foreground-muted">{formatDateTime(order.created_at)}</p>
                    </div>
                    <OrderStatusBadge status={order.status} />
                    <span className="text-sm font-semibold text-foreground">{formatPriceVnd(order.total_amount)}</span>
                  </div>
                ))}
              </div>
              {ordersTotalPages > 1 && (
                <div className="mt-3 flex items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => setOrdersPage((p) => p - 1)}
                    disabled={ordersPage <= 1}
                    className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Trang trước
                  </button>
                  <span className="text-sm text-foreground-muted">
                    Trang {ordersPage}/{ordersTotalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setOrdersPage((p) => p + 1)}
                    disabled={ordersPage >= ordersTotalPages}
                    className="rounded-lg border border-border px-4 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Trang sau
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
