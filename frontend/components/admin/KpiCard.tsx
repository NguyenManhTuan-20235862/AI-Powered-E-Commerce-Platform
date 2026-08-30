/**
 * Thẻ KPI tổng quan (task 5.3.2, port từ Stitch) - CHỈ 3 số liệu THẬT có sẵn
 * từ `GET /admin/dashboard/summary` (`total_revenue`/`total_orders`/
 * `new_users`) - CỐ TÌNH bỏ badge xu hướng "+12.5%" trong thiết kế gốc: API
 * không trả về số liệu so sánh kỳ trước, hiện số bịa sẽ vi phạm nguyên tắc
 * "không có API thì không hiện" xuyên suốt dự án.
 *
 * Icon dùng SVG inline (KHÔNG dùng font `material-symbols-outlined` như
 * file Stitch gốc) - khớp convention TOÀN BỘ icon hiện có trong dự án
 * (Header, ChatWidget, Sidebar... đều SVG inline, chưa từng dùng icon font
 * nào) - không thêm 1 cách làm icon thứ 2 chỉ cho riêng dashboard.
 */
export function KpiCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex flex-col justify-between gap-4 rounded-xl bg-surface p-6 transition-transform duration-300 hover:-translate-y-1">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary">
          {icon}
        </div>
        <span className="text-sm font-semibold text-foreground-secondary">{label}</span>
      </div>
      <p className="font-heading text-3xl text-primary">{value}</p>
    </div>
  );
}
