"use client";

import Link from "next/link";

import { OrderStatusBadge } from "@/components/order/OrderStatusBadge";
import { OrderStatusSelect } from "@/components/admin/OrderStatusSelect";
import { formatPriceVnd } from "@/lib/format";
import type { Order, OrderStatus } from "@/types/order";

const STATUS_FILTER_OPTIONS: { value: OrderStatus | ""; label: string }[] = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "pending", label: "Chờ xác nhận" },
  { value: "confirmed", label: "Đã xác nhận" },
  { value: "shipping", label: "Đang giao" },
  { value: "delivered", label: "Đã giao" },
  { value: "cancelled", label: "Đã hủy" },
];

// Cùng hàm format ngày với OrderCard.tsx (task 4.3.3) - không tách ra
// lib/format.ts dùng chung vì chỉ 1 dòng, tách thêm 1 hàm export cho đúng 2
// nơi dùng không đáng - cùng mức độ tối giản đã áp dụng cho các phần trùng
// nhỏ khác trong dự án.
function formatOrderDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/**
 * Client Component (task 4.4.2) - bảng danh sách đơn hàng Admin, HTML
 * `<table>` thuần (cùng quyết định `ProductTable.tsx` - quy mô đồ án không
 * cần thư viện table). Cột "Trạng thái" tách riêng badge HIỂN THỊ
 * (`OrderStatusBadge`, tái sử dụng nguyên vẹn từ task 4.3.3) và cột "Hành
 * động" chứa dropdown ĐỔI trạng thái (`OrderStatusSelect`) + nút "Xem chi
 * tiết" - đúng cấu trúc thật đã xác nhận ở `code.html` Stitch (case a: 1
 * badge display-only + 1 select thật, KHÔNG PHẢI text tĩnh lặp lại).
 *
 * "Xem chi tiết" trỏ THẲNG vào `/orders/{id}` (route stub đã có sẵn từ task
 * 4.3.3, dùng chung với Customer - `GET /orders/{id}` cho phép cả chủ đơn
 * lẫn Admin xem) thay vì xây trang chi tiết riêng cho Admin - phạm vi task
 * 4.4.2 chỉ gồm bảng danh sách + đổi trạng thái inline + search/filter,
 * trang chi tiết Admin riêng (nếu cần khác gì trang Customer) để dành cho
 * task sau.
 */
export function OrderTable({
  orders,
  isLoading,
  search,
  onSearchChange,
  status,
  onStatusChange,
  page,
  totalPages,
  onPageChange,
  onChanged,
}: {
  orders: Order[];
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  status: OrderStatus | "";
  onStatusChange: (value: OrderStatus | "") => void;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onChanged: () => void;
}) {
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
            placeholder="Tìm theo mã đơn hàng hoặc tên khách hàng..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-primary"
          />
        </div>
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value as OrderStatus | "")}
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
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Mã đơn hàng</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Khách hàng</th>
              <th className="px-4 py-3 text-xs font-semibold text-foreground-secondary">Ngày đặt</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-foreground-secondary">Tổng tiền</th>
              <th className="w-32 px-4 py-3 text-xs font-semibold text-foreground-secondary">Trạng thái</th>
              <th className="w-56 px-4 py-3 text-xs font-semibold text-foreground-secondary">Hành động</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-foreground-muted">
                  Đang tải...
                </td>
              </tr>
            ) : orders.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-foreground-muted">
                  Không có đơn hàng nào khớp bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.id} className="hover:bg-primary-100/40">
                  <td className="px-4 py-2 text-sm font-medium text-foreground">#{order.id}</td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">
                    <div>{order.shipping_name}</div>
                    <div className="text-xs text-foreground-muted">{order.shipping_phone}</div>
                  </td>
                  <td className="px-4 py-2 text-sm text-foreground-secondary">{formatOrderDate(order.created_at)}</td>
                  <td className="px-4 py-2 text-right text-sm font-semibold text-primary">
                    {formatPriceVnd(order.total_amount)}
                  </td>
                  <td className="px-4 py-2">
                    <OrderStatusBadge status={order.status} />
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <OrderStatusSelect order={order} onChanged={onChanged} />
                      <Link
                        href={`/orders/${order.id}`}
                        title="Xem chi tiết"
                        className="shrink-0 rounded p-1.5 text-foreground-muted hover:bg-primary-100 hover:text-primary"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                          <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z" strokeLinecap="round" strokeLinejoin="round" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 border-t border-border px-4 py-3">
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
    </div>
  );
}
