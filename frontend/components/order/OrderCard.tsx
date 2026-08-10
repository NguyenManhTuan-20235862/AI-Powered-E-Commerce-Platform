"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { OrderStatusBadge } from "@/components/order/OrderStatusBadge";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { Order } from "@/types/order";

function formatOrderDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// order_items là snapshot BẤT BIẾN, CỐ TÌNH không có field ảnh sản phẩm
// (xem docstring OrderItemRead, backend/app/schemas/order.py) - card ở đây
// CHỈ hiện text (tên + số lượng), KHÔNG có thumbnail như thiết kế Stitch gốc
// (quyết định đã thống nhất lúc audit thiết kế task 4.3.3, tránh join dữ
// liệu sản phẩm HIỆN TẠI vào 1 đơn hàng đã chốt trong quá khứ).
function itemsSummary(order: Order): string {
  if (order.items.length === 0) return "";
  const first = order.items[0].product_name;
  return order.items.length === 1 ? first : `${first} và ${order.items.length - 1} sản phẩm khác`;
}

/**
 * Client Component (task 4.3.3) - 1 card đơn hàng trong danh sách. Nút "Hủy
 * đơn" CHỈ hiện khi `status === "pending"` (khớp `cancel_order()` Backend -
 * chỉ cho hủy đơn pending, xem app/services/order_service.py) - `confirm()`
 * trình duyệt trước khi gọi API (tránh bấm nhầm, chưa có modal component
 * riêng trong dự án nên dùng thẳng primitive có sẵn, phù hợp quy mô đồ án).
 * Hủy thành công/thất bại đều toast; danh sách cập nhật qua `onCancelled`
 * (cha tự refetch lại đúng theo tab đang chọn, KHÔNG tự patch state ở đây -
 * đơn hủy xong có thể không còn khớp tab "Chờ xác nhận" đang xem, refetch
 * đảm bảo danh sách luôn đúng thay vì để lại dòng lệch trạng thái).
 */
export function OrderCard({ order, onCancelled }: { order: Order; onCancelled: () => void }) {
  const [isCancelling, setIsCancelling] = useState(false);

  async function handleCancel() {
    if (!window.confirm(`Xác nhận hủy đơn hàng #${order.id}? Hành động này không thể hoàn tác.`)) return;
    setIsCancelling(true);
    try {
      await api.put<ApiResponse<Order>>(`/orders/${order.id}/cancel`);
      toast.success("Đã hủy đơn hàng");
      onCancelled();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Hủy đơn hàng thất bại. Vui lòng thử lại."));
      setIsCancelling(false);
    }
  }

  return (
    <div className={`flex flex-col gap-3 rounded-xl bg-surface p-5 shadow-sm ${order.status === "cancelled" ? "opacity-70" : ""}`}>
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <span className="font-semibold text-foreground">#{order.id}</span>
          <span className="ml-2 text-sm text-foreground-muted">{formatOrderDate(order.created_at)}</span>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>

      <div className="py-1">
        <p className="font-semibold text-foreground">{itemsSummary(order)}</p>
        <p className="text-sm text-foreground-muted">
          {order.items.reduce((sum, item) => sum + item.quantity, 0)} sản phẩm
        </p>
      </div>

      <div className="flex flex-col items-start justify-between gap-3 border-t border-border pt-3 sm:flex-row sm:items-center">
        <div>
          <span className="text-sm text-foreground-muted">Tổng tiền: </span>
          <span className="font-heading text-lg text-primary">{formatPriceVnd(order.total_amount)}</span>
        </div>
        <div className="flex gap-3">
          {order.status === "pending" && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling}
              className="text-sm text-foreground-muted transition-colors hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCancelling ? "Đang hủy..." : "Hủy đơn"}
            </button>
          )}
          <Link
            href={`/orders/${order.id}`}
            className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-primary-100"
          >
            Xem chi tiết
          </Link>
        </div>
      </div>
    </div>
  );
}
