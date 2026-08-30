"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TooltipContentProps } from "recharts";

import { CHART_COLOR_AXIS_TEXT, CHART_COLOR_GRID, CHART_COLOR_PRIMARY } from "@/lib/chart-colors";
import { formatPriceVnd } from "@/lib/format";
import type { RevenuePoint } from "@/types/dashboard";

/**
 * Tooltip dạng "bubble" (bo góc + border + đổ bóng ấm) khớp phong cách thiết
 * kế Stitch - render qua HTML/DOM overlay (không phải SVG) nên dùng thẳng
 * class Tailwind + token (`bg-surface`/`border-border`/`shadow-warm`/
 * `text-primary`), KHÔNG dùng `contentStyle` (inline hex) của Recharts.
 */
function RevenueTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const revenue = Number(payload[0]?.value ?? 0);
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-2 shadow-warm">
      <p className="text-xs font-semibold text-foreground-muted">{label}</p>
      <p className="font-heading text-base text-primary">{formatPriceVnd(String(revenue))}</p>
    </div>
  );
}

/**
 * Line chart doanh thu theo ngày/tuần/tháng (task 5.3.2) - `data` là
 * `RevenuePointRead[]` thật từ `GET /admin/dashboard/revenue` (mảng LIÊN TỤC,
 * đã điền 0 cho khoảng trống ở Backend - xem `dashboard_service.py`), KHÔNG
 * tự xử lý gap ở đây.
 *
 * Màu `stroke`/gradient CỐ ĐỊNH `CHART_COLOR_PRIMARY` (`#c67139`) - KHÔNG
 * dùng bảng màu mặc định Recharts (tự sinh rainbow nếu thiếu `stroke`).
 */
export function RevenueChart({ data }: { data: RevenuePoint[] }) {
  const chartData = data.map((point) => ({ period: point.period, revenue: Number(point.revenue) }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revenue-area-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART_COLOR_PRIMARY} stopOpacity={0.25} />
            <stop offset="100%" stopColor={CHART_COLOR_PRIMARY} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={CHART_COLOR_GRID} strokeOpacity={0.2} vertical={false} />
        <XAxis
          dataKey="period"
          tick={{ fill: CHART_COLOR_AXIS_TEXT, fontSize: 12 }}
          axisLine={{ stroke: CHART_COLOR_GRID, strokeOpacity: 0.2 }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: CHART_COLOR_AXIS_TEXT, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={(value: number) => (value >= 1_000_000 ? `${value / 1_000_000}tr` : String(value))}
        />
        <Tooltip content={RevenueTooltip} />
        <Area
          type="monotone"
          dataKey="revenue"
          stroke={CHART_COLOR_PRIMARY}
          strokeWidth={3}
          fill="url(#revenue-area-gradient)"
          dot={false}
          activeDot={{ r: 5, fill: CHART_COLOR_PRIMARY }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
