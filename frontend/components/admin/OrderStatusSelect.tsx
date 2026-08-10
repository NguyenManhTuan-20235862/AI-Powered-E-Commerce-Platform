"use client";

import { useState } from "react";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import type { ApiResponse } from "@/types/common";
import type { Order, OrderStatus } from "@/types/order";

// Mirror CHÍNH XÁC `VALID_STATUS_TRANSITIONS` thật
// (backend/app/services/order_service.py, task 3.4.2/4.4.2) - đây là nguồn
// sự thật DUY NHẤT cho state machine trạng thái đơn hàng, dropdown ở đây chỉ
// đọc lại (KHÔNG tự bịa thêm/bớt lựa chọn). Backend chưa có endpoint riêng
// trả về danh sách transition hợp lệ (thêm 1 endpoint chỉ để tránh duplicate
// object 5 dòng này không hợp lý ở quy mô đồ án) - nếu sau này Backend đổi
// state machine, PHẢI tự sửa lại đúng theo ở đây.
const VALID_STATUS_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["shipping", "cancelled"],
  shipping: ["delivered"],
  delivered: [],
  cancelled: [],
};

// Cùng nhãn tiếng Việt với OrderStatusBadge.tsx (task 4.3.3) - component đó
// không export map nhãn riêng nên khai báo lại ở đây, chỉ dùng làm text
// hiển thị trong <option>/hộp thoại confirm, KHÔNG liên quan phần màu sắc
// (OrderStatusBadge vẫn được tái sử dụng nguyên vẹn cho phần badge).
const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  shipping: "Đang giao",
  delivered: "Đã giao",
  cancelled: "Đã hủy",
};

/**
 * Client Component (task 4.4.2) - dropdown đổi trạng thái đơn hàng ở bảng
 * Admin. CHỈ hiện các lựa chọn hợp lệ theo `VALID_STATUS_TRANSITIONS` của
 * trạng thái HIỆN TẠI của đơn (không cho chọn tự do cả 5 trạng thái) -
 * disable HOÀN TOÀN khi đang ở trạng thái terminal (`delivered`/`cancelled`,
 * danh sách transition rỗng).
 *
 * `window.confirm()` trước khi gọi API - cùng pattern
 * `OrderCard.tsx:handleCancel` (task 4.3.3, tránh bấm nhầm đổi trạng thái,
 * chưa có modal component riêng trong dự án). Đổi thành công gọi `onChanged`
 * (cha refetch lại bảng - KHÔNG tự patch state cục bộ, cùng lý do đã áp dụng
 * cho `OrderCard`: đơn giản, luôn đúng theo filter/trang đang xem).
 */
export function OrderStatusSelect({ order, onChanged }: { order: Order; onChanged: () => void }) {
  const [isUpdating, setIsUpdating] = useState(false);
  const nextOptions = VALID_STATUS_TRANSITIONS[order.status];
  const isTerminal = nextOptions.length === 0;

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const nextStatus = e.target.value as OrderStatus;
    if (!nextStatus || nextStatus === order.status) return;

    const confirmed = window.confirm(
      `Xác nhận đổi trạng thái đơn #${order.id} từ "${STATUS_LABELS[order.status]}" sang "${STATUS_LABELS[nextStatus]}"?`,
    );
    if (!confirmed) {
      e.target.value = order.status;
      return;
    }

    setIsUpdating(true);
    try {
      await api.put<ApiResponse<Order>>(`/orders/${order.id}/status`, { status: nextStatus });
      toast.success("Đã cập nhật trạng thái đơn hàng");
      onChanged();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Cập nhật trạng thái thất bại. Vui lòng thử lại."));
      e.target.value = order.status;
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <select
      aria-label={`Đổi trạng thái đơn #${order.id}`}
      value={order.status}
      onChange={handleChange}
      disabled={isTerminal || isUpdating}
      className="w-full min-w-[9.5rem] rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-primary disabled:cursor-not-allowed disabled:opacity-60"
    >
      <option value={order.status}>{STATUS_LABELS[order.status]}</option>
      {nextOptions.map((status) => (
        <option key={status} value={status}>
          {STATUS_LABELS[status]}
        </option>
      ))}
    </select>
  );
}
