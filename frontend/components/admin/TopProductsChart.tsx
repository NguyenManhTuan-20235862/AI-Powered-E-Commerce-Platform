import { formatPriceVnd } from "@/lib/format";
import type { TopProduct, TopProductSortBy } from "@/types/dashboard";

/**
 * Danh sách xếp hạng sản phẩm bán chạy (task 5.3.2) - port THEO ĐÚNG dạng
 * "ranked list + progress bar" của thiết kế Stitch (không dùng Recharts
 * `<BarChart>` trục số - thiết kế gốc vốn chỉ là các thanh % đơn giản, không
 * có trục/tick, "list ranked" khớp hơn `docs`/kế hoạch đã thống nhất).
 *
 * Stitch gốc hiện % CỐ ĐỊNH kiểu "42%/28%/18%/12%" (ngụ ý % trên tổng, dữ
 * liệu KHÔNG có thật) - đổi sang % TƯƠNG ĐỐI so với sản phẩm ĐỨNG ĐẦU danh
 * sách (item #1 luôn full-width 100%, các item sau tỉ lệ theo đúng
 * `quantity_sold`/`revenue` thật tùy `sortBy`) - trung thực với dữ liệu thật
 * thay vì bịa "% trên tổng doanh số" (top N sản phẩm không đại diện 100%
 * tổng doanh số toàn hệ thống).
 *
 * Màu thanh xen kẽ `bg-primary`/`bg-secondary` theo thứ hạng chẵn/lẻ - đúng
 * màu token thật, khớp cách phối màu xen kẽ của thiết kế gốc.
 */
export function TopProductsChart({ items, sortBy }: { items: TopProduct[]; sortBy: TopProductSortBy }) {
  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-foreground-muted">Chưa có dữ liệu bán hàng trong khoảng thời gian này.</p>;
  }

  const maxValue = Math.max(...items.map((item) => (sortBy === "quantity" ? item.quantity_sold : Number(item.revenue))));

  return (
    <div className="flex flex-1 flex-col justify-around gap-4">
      {items.map((item, index) => {
        const rawValue = sortBy === "quantity" ? item.quantity_sold : Number(item.revenue);
        const widthPercent = maxValue > 0 ? (rawValue / maxValue) * 100 : 0;
        const displayValue = sortBy === "quantity" ? `${item.quantity_sold} đã bán` : formatPriceVnd(item.revenue);
        const isEven = index % 2 === 0;

        return (
          <div key={item.product_id}>
            <div className="mb-1 flex justify-between text-sm text-foreground-secondary">
              <span>{item.name}</span>
              <span className="font-bold">{displayValue}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary-100">
              <div
                className={`h-full rounded-full ${isEven ? "bg-primary" : "bg-secondary"}`}
                style={{ width: `${widthPercent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
