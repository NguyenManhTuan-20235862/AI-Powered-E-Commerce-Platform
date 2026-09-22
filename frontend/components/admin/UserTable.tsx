"use client";

import { useState } from "react";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPaginationRange } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { AdminUser, UserRole } from "@/types/user";

const ROLE_FILTER_OPTIONS: { value: UserRole | ""; label: string }[] = [
  { value: "", label: "Tất cả vai trò" },
  { value: "admin", label: "Admin" },
  { value: "customer", label: "Customer" },
];

const STATUS_FILTER_OPTIONS: { value: "" | "true" | "false"; label: string }[] = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "true", label: "Đang hoạt động" },
  { value: "false", label: "Đã khóa" },
];

function formatJoinDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function RoleBadge({ role }: { role: UserRole }) {
  const className =
    role === "admin" ? "bg-primary-800 text-white" : "bg-primary-100 text-primary-800";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {role === "admin" ? "Admin" : "Customer"}
    </span>
  );
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  const className = isActive ? "bg-secondary-100 text-secondary-800" : "bg-error-container text-error";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {isActive ? "Đang hoạt động" : "Đã khóa"}
    </span>
  );
}

/**
 * Client Component (port từ Stitch, task Quản lý người dùng Admin) - bảng
 * user, HTML `<table>` thuần (cùng quyết định `ProductTable.tsx`/
 * `OrderTable.tsx` - quy mô đồ án không cần thư viện table).
 *
 * Nút "Khóa"/"Mở khóa" CỐ TÌNH KHÔNG hiện ở hàng `role === "admin"` (khớp
 * ĐÚNG thiết kế Stitch - cột "Hành động" của user Admin chỉ có "—") - ĐÃ
 * khớp thêm giới hạn Backend thật (task "Hoàn thiện quản lý tài khoản
 * Admin"): `PUT /users/{id}/status` giờ trả 403 nếu target là BẤT KỲ Admin
 * nào (kể cả tự khóa chính mình, xem `app/routers/user.py`) - UI ẩn nút
 * trước để tránh 1 request 403 vô ích, KHÔNG còn là giới hạn UI đơn thuần
 * như trước (trước đây API cho phép, chỉ UI tự chặn).
 *
 * `window.confirm()` trước khi khóa (hành động nhạy cảm) - cùng pattern
 * `OrderCard.tsx:handleCancel()`/`OrderStatusSelect.tsx` - CHỈ confirm lúc
 * KHÓA (mở khóa không cần, không có rủi ro tương đương).
 *
 * Nút "Chi tiết" (mọi role, kể cả Admin - xem là được, chỉ KHÓA mới chặn) mở
 * `UserDetailModal` (cha quản lý qua `onViewDetail`) - hiện thông tin đầy đủ
 * + lịch sử đơn hàng, đóng `GET /users/{id}` (trước đó không nơi nào gọi).
 *
 * Khóa/mở khóa xong KHÔNG gọi lại `fetchUsers()` (toàn bảng) - `onChanged`
 * nhận thẳng `AdminUser` mới nhất từ response `PUT` (đã có sẵn, trước đây bỏ
 * qua), cha (`page.tsx`) patch ĐÚNG 1 dòng trong state cục bộ. Đánh đổi đã
 * chấp nhận: nếu đang lọc theo `isActive` và dòng vừa đổi không còn khớp bộ
 * lọc, dòng đó vẫn hiện tạm (không tự biến mất) tới lần fetch tự nhiên kế
 * tiếp (đổi trang/filter/tìm kiếm) - đơn giản hơn hẳn so với tự đồng bộ lại
 * `total`/`totalPages` cho 1 tình huống không thường xuyên.
 */
export function UserTable({
  users,
  isLoading,
  search,
  onSearchChange,
  role,
  onRoleChange,
  isActive,
  onStatusChange,
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  onChanged,
  onViewDetail,
}: {
  users: AdminUser[];
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  role: UserRole | "";
  onRoleChange: (value: UserRole | "") => void;
  isActive: "" | "true" | "false";
  onStatusChange: (value: "" | "true" | "false") => void;
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  // Nhận LUÔN `AdminUser` mới nhất từ response `PUT /users/{id}/status` (đã
  // có sẵn, trước đây chỉ đọc message rồi bỏ) - cha patch thẳng dòng đó
  // trong state cục bộ, KHÔNG cần `fetchUsers()` lại toàn bảng.
  onChanged: (updated: AdminUser) => void;
  onViewDetail: (userId: number) => void;
}) {
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const { start, end } = formatPaginationRange(page, pageSize, total);

  async function handleToggleActive(user: AdminUser) {
    if (user.is_active) {
      const confirmed = window.confirm(`Xác nhận khóa tài khoản "${user.full_name}" (${user.email})?`);
      if (!confirmed) return;
    }

    setUpdatingId(user.id);
    try {
      const { data } = await api.put<ApiResponse<AdminUser>>(`/users/${user.id}/status`, { is_active: !user.is_active });
      toast.success(user.is_active ? "Đã khóa tài khoản" : "Đã mở khóa tài khoản");
      onChanged(data.data);
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Cập nhật trạng thái thất bại. Vui lòng thử lại."));
    } finally {
      setUpdatingId(null);
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
            placeholder="Tìm theo tên hoặc email..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-primary"
          />
        </div>
        <div className="flex w-full gap-3 sm:w-auto">
          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value as UserRole | "")}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary sm:w-40"
          >
            {ROLE_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={isActive}
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
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border bg-background">
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Họ tên</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Email</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Số điện thoại</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Vai trò</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Ngày tham gia</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Trạng thái</th>
              <th className="w-56 px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Đang tải...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-foreground-muted">
                  Không có người dùng nào khớp bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-primary-100/40">
                  <td className="px-4 py-2 text-sm font-medium text-foreground">{user.full_name}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{user.email}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{user.phone ?? "—"}</td>
                  <td className="px-4 py-2">
                    <RoleBadge role={user.role} />
                  </td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{formatJoinDate(user.created_at)}</td>
                  <td className="px-4 py-2">
                    <StatusBadge isActive={user.is_active} />
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => onViewDetail(user.id)}
                        className="rounded border border-border px-3 py-1.5 text-sm text-foreground-secondary transition-colors hover:border-primary hover:text-primary"
                      >
                        Chi tiết
                      </button>
                      {user.role === "admin" ? (
                        <span className="w-[76px] text-center text-foreground-muted">—</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleToggleActive(user)}
                          disabled={updatingId === user.id}
                          className={
                            user.is_active
                              ? "rounded border border-foreground-muted px-4 py-1.5 text-sm text-foreground-secondary transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                              : "rounded border border-primary px-4 py-1.5 text-sm text-primary transition-colors hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50"
                          }
                        >
                          {updatingId === user.id ? "..." : user.is_active ? "Khóa" : "Mở khóa"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {!isLoading && users.length > 0 && (
          <div className="flex flex-col items-center justify-between gap-2 border-t border-border px-4 py-3 sm:flex-row">
            <span className="text-sm text-foreground-muted">
              Hiển thị {start}-{end} trên tổng {total} người dùng
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
