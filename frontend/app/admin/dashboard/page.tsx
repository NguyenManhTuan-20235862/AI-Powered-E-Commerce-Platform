"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { KpiCard } from "@/components/admin/KpiCard";
import { RevenueChart } from "@/components/admin/RevenueChart";
import { TopProductsChart } from "@/components/admin/TopProductsChart";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { DashboardSummary, RevenueInterval, RevenuePoint, TopProduct, TopProductSortBy } from "@/types/dashboard";

const TOP_PRODUCTS_SORT_BY: TopProductSortBy = "quantity";

function IconPayments() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="6" width="20" height="12" rx="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconCart() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 4h2l2.4 12.2a2 2 0 0 0 2 1.8h7.2a2 2 0 0 0 2-1.6L20 8H6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9" cy="20" r="1" /><circle cx="17" cy="20" r="1" />
    </svg>
  );
}

function IconUserAdd() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="9" cy="8" r="3.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M2.5 19c0-3.3 2.9-6 6.5-6s6.5 2.7 6.5 6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M18 8v6M15 11h6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const INTERVAL_OPTIONS: { value: RevenueInterval; label: string }[] = [
  { value: "day", label: "Ngày" },
  { value: "week", label: "Tuần" },
  { value: "month", label: "Tháng" },
];

const INTERVAL_CHART_TITLE: Record<RevenueInterval, string> = {
  day: "Doanh thu theo ngày",
  week: "Doanh thu theo tuần",
  month: "Doanh thu theo tháng",
};

/**
 * Dashboard thống kê Admin (task 5.3.2, port từ Stitch; hoàn thiện thêm ở
 * task "Hoàn thiện dashboard và realtime Admin") - Client Component (CSR
 * toàn trang, cùng lý do `OrdersView.tsx`: trang cá nhân sau xác thực, cần
 * tương tác refresh, không có giá trị SEO). Gọi 3 API thật (task 5.3.1) song
 * song lúc mount + khi đổi khoảng ngày/interval + khi bấm "Làm mới" - KHÔNG
 * cache phía Frontend (mỗi lần gọi đều là request thật, để Backend Redis
 * (TTL 5 phút) tự quyết định trả cache hay tính lại).
 *
 * **Vẫn giữ NGUYÊN thiết kế "fetch khi mở trang/bấm làm mới"** (quyết định
 * task 5.3, đã xác nhận lại ở task này) - KHÔNG đẩy dữ liệu qua SSE/WebSocket,
 * số liệu tổng hợp không cần tức thời như 1 sự kiện đơn lẻ (khác trạng thái
 * đơn hàng ở 5.1/5.2).
 *
 * **Bộ lọc khoảng ngày + interval CHUNG 1 `useEffect`** (đổi 1 trong 2 đều
 * refetch CẢ 3 API, kể cả khi chỉ `interval` đổi - vốn chỉ ảnh hưởng
 * `/revenue`) - đơn giản hơn hẳn tách 2 effect riêng, chấp nhận 2 lệnh gọi dư
 * (`summary`/`top-products`) khi chỉ đổi interval vì Backend đã cache Redis
 * (TTL 5 phút, cùng tham số) - cache hit gần như tức thời, không đáng đổi lấy
 * độ phức tạp thêm 1 effect + 1 hàm fetch riêng cho quy mô đồ án.
 *
 * `dateFrom`/`dateTo` (input) mặc định RỖNG (để Backend tự áp dụng 30 ngày
 * gần nhất) - sau lần fetch ĐẦU TIÊN thành công, tự điền lại bằng
 * `summary.date_from`/`date_to` THẬT Backend đã áp dụng (CHỈ 1 LẦN, xem guard
 * trong `fetchAll`) - Admin thấy đúng khoảng ngày đang áp dụng ngay cả khi
 * chưa tự chọn gì, khớp đoạn text "Dữ liệu từ ... đến ..." bên dưới.
 *
 * Validate `date_from <= date_to` CẢ 2 phía - Frontend chặn TRƯỚC khi gọi API
 * (hiện cảnh báo inline, không gọi request chắc chắn 400) + Backend vẫn tự
 * validate lại (`dashboard_service.resolve_date_range()`) làm tuyến phòng thủ
 * cuối nếu Frontend có lỗi/bị bỏ qua.
 *
 * KHÔNG port thẻ KPI "Tỷ lệ chuyển đổi" (4.8%) từ thiết kế gốc - không có
 * API nào cung cấp số liệu này, hiện số bịa vi phạm nguyên tắc "không có dữ
 * liệu thật thì không hiện" xuyên suốt dự án.
 */
export default function AdminDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  // Đặt tên khác "interval"/"setInterval" (dù đúng ngữ nghĩa hơn) - tránh che
  // khuất hàm toàn cục `window.setInterval` cùng tên, dễ gây nhầm lẫn/bug về
  // sau nếu file này cần dùng timer thật.
  const [revenueInterval, setRevenueInterval] = useState<RevenueInterval>("day");

  const hasAppliedDefaultRange = useRef(false);
  const invalidRange = Boolean(dateFrom && dateTo && dateFrom > dateTo);

  const fetchAll = useCallback(async () => {
    if (invalidRange) return;
    setIsLoading(true);
    setLoadError(false);
    try {
      const rangeParams: Record<string, string> = {};
      if (dateFrom) rangeParams.date_from = dateFrom;
      if (dateTo) rangeParams.date_to = dateTo;

      const [summaryRes, revenueRes, topProductsRes] = await Promise.all([
        api.get<ApiResponse<DashboardSummary>>("/admin/dashboard/summary", { params: rangeParams }),
        api.get<ApiResponse<RevenuePoint[]>>("/admin/dashboard/revenue", {
          params: { ...rangeParams, interval: revenueInterval },
        }),
        api.get<ApiResponse<TopProduct[]>>("/admin/dashboard/top-products", {
          params: { ...rangeParams, sort_by: TOP_PRODUCTS_SORT_BY },
        }),
      ]);
      setSummary(summaryRes.data.data);
      setRevenue(revenueRes.data.data);
      setTopProducts(topProductsRes.data.data);

      // Điền lại `dateFrom`/`dateTo` bằng khoảng THẬT Backend đã áp dụng - CHỈ
      // 1 LẦN (guard bằng ref, không phải state, để KHÔNG kích hoạt lại chính
      // effect đang chạy hàm này) khi Admin CHƯA tự chọn gì (cả 2 field còn rỗng).
      if (!hasAppliedDefaultRange.current && !dateFrom && !dateTo) {
        hasAppliedDefaultRange.current = true;
        setDateFrom(summaryRes.data.data.date_from);
        setDateTo(summaryRes.data.data.date_to);
      }
    } catch (err) {
      setLoadError(true);
      toast.error(extractApiErrorMessage(err, "Không tải được dữ liệu thống kê. Vui lòng thử lại."));
    } finally {
      setIsLoading(false);
    }
  }, [dateFrom, dateTo, revenueInterval, invalidRange]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl text-primary-800">Tổng quan</h2>
          <p className="mt-2 text-foreground-secondary">
            {summary ? `Dữ liệu từ ${summary.date_from} đến ${summary.date_to}.` : "Dữ liệu hoạt động kinh doanh."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1 text-sm text-foreground-secondary">
            Từ
            <input
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </label>
          <label className="flex items-center gap-1 text-sm text-foreground-secondary">
            Đến
            <input
              type="date"
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </label>
          <button
            type="button"
            onClick={fetchAll}
            disabled={isLoading || invalidRange}
            className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 11A8 8 0 1 0 6.3 17.7M20 11V5M20 11h-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {isLoading ? "Đang tải..." : "Làm mới"}
          </button>
        </div>
      </div>

      {invalidRange && (
        <p className="mb-4 rounded-lg bg-error-container px-4 py-2 text-sm text-error">
          &quot;Từ&quot; phải trước hoặc bằng &quot;Đến&quot; - chỉnh lại khoảng ngày để tải dữ liệu.
        </p>
      )}

      {isLoading && !summary ? (
        <div className="py-24 text-center text-foreground-muted">Đang tải dữ liệu thống kê...</div>
      ) : loadError ? (
        <div className="flex flex-col items-center gap-3 py-24 text-center">
          <p className="text-error">Không tải được dữ liệu thống kê. Vui lòng thử lại.</p>
          <button
            type="button"
            onClick={fetchAll}
            className="rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
          >
            Thử lại
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <KpiCard icon={<IconPayments />} label="Tổng doanh thu" value={summary ? formatPriceVnd(summary.total_revenue) : "-"} />
          </div>
          <KpiCard icon={<IconCart />} label="Tổng đơn hàng" value={summary ? String(summary.total_orders) : "-"} />
          <KpiCard icon={<IconUserAdd />} label="Khách hàng mới" value={summary ? String(summary.new_users) : "-"} />

          <div className="rounded-xl bg-surface p-6 md:col-span-3">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-heading text-xl text-foreground">{INTERVAL_CHART_TITLE[revenueInterval]}</h3>
              <div className="flex gap-1 rounded-full border border-border p-1">
                {INTERVAL_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setRevenueInterval(option.value)}
                    className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                      revenueInterval === option.value
                        ? "bg-primary text-white"
                        : "text-foreground-secondary hover:bg-primary-100"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            {revenue.length === 0 ? (
              <p className="py-16 text-center text-sm text-foreground-muted">Chưa có dữ liệu doanh thu trong khoảng thời gian này.</p>
            ) : (
              <RevenueChart data={revenue} />
            )}
          </div>

          <div className="flex flex-col rounded-xl bg-surface p-6 md:col-span-1">
            <h3 className="mb-6 font-heading text-xl text-foreground">Sản phẩm bán chạy</h3>
            <TopProductsChart items={topProducts} sortBy={TOP_PRODUCTS_SORT_BY} />
          </div>
        </div>
      )}
    </div>
  );
}
