import type { OrderStatus } from "@/types/order";

/**
 * Map trạng thái đơn hàng -> màu/nhãn hiển thị (task 4.3.3). Thiết kế Stitch
 * chỉ minh họa 3/5 trạng thái (pending/delivered/cancelled) - `confirmed`/
 * `shipping` tự chọn thêm, dùng CHỈ token thật đã có (`primary`/`secondary`/
 * `error`, không có token thứ 4/5 nào khác trong dự án), thể hiện mức độ
 * tiến triển bằng độ đậm nhạt của `primary`: pending (nhạt nhất, mới bắt
 * đầu) -> confirmed -> shipping (đậm nhất, đang diễn ra) -> delivered
 * (secondary, thành công) -> cancelled (error, khớp đúng màu Stitch dùng).
 */
const STATUS_CONFIG: Record<OrderStatus, { label: string; className: string }> = {
  pending: { label: "Chờ xác nhận", className: "bg-primary-100 text-primary-800" },
  confirmed: { label: "Đã xác nhận", className: "bg-primary-300 text-primary-800" },
  shipping: { label: "Đang giao", className: "bg-primary text-background" },
  delivered: { label: "Đã giao", className: "bg-secondary text-background" },
  cancelled: { label: "Đã hủy", className: "bg-error-container text-error" },
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={`inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-semibold ${config.className}`}>
      {config.label}
    </span>
  );
}
