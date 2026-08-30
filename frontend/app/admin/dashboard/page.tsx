"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { KpiCard } from "@/components/admin/KpiCard";
import { RevenueChart } from "@/components/admin/RevenueChart";
import { TopProductsChart } from "@/components/admin/TopProductsChart";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { formatPriceVnd } from "@/lib/format";
import type { ApiResponse } from "@/types/common";
import type { DashboardSummary, RevenuePoint, TopProduct, TopProductSortBy } from "@/types/dashboard";

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

/**
 * Dashboard thống kê Admin (task 5.3.2, port từ Stitch) - Client Component
 * (CSR toàn trang, cùng lý do `OrdersView.tsx`: trang cá nhân sau xác thực,
 * cần tương tác refresh, không có giá trị SEO). Gọi 3 API thật (task 5.3.1)
 * song song lúc mount + khi bấm "Làm mới" - KHÔNG cache phía Frontend (mỗi
 * lần gọi đều là request thật, để Backend Redis (TTL 5 phút) tự quyết định
 * trả cache hay tính lại - Frontend không tự giữ state cache riêng chồng lên).
 *
 * KHÔNG có bộ chọn khoảng ngày (nút "Date Range" trong thiết kế Stitch giữ
 * lại nhưng để DECORATIVE/disabled) - ngoài phạm vi task 5.3.2 (chỉ yêu cầu
 * fetch mặc định 30 ngày + nút "Làm mới"), cùng cách xử lý phần chưa làm đã
 * áp dụng cho radio VNPay/Momo ở `CheckoutForm.tsx`.
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

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    try {
      const [summaryRes, revenueRes, topProductsRes] = await Promise.all([
        api.get<ApiResponse<DashboardSummary>>("/admin/dashboard/summary"),
        api.get<ApiResponse<RevenuePoint[]>>("/admin/dashboard/revenue", { params: { interval: "day" } }),
        api.get<ApiResponse<TopProduct[]>>("/admin/dashboard/top-products", { params: { sort_by: TOP_PRODUCTS_SORT_BY } }),
      ]);
      setSummary(summaryRes.data.data);
      setRevenue(revenueRes.data.data);
      setTopProducts(topProductsRes.data.data);
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Không tải được dữ liệu thống kê. Vui lòng thử lại."));
    } finally {
      setIsLoading(false);
    }
  }, []);

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
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Sắp ra mắt"
            className="hidden items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground-secondary opacity-50 md:flex"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <path d="M3 9h18M8 2v4M16 2v4" strokeLinecap="round" />
            </svg>
            Khoảng ngày
          </button>
          <button
            type="button"
            onClick={fetchAll}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 11A8 8 0 1 0 6.3 17.7M20 11V5M20 11h-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {isLoading ? "Đang tải..." : "Làm mới"}
          </button>
        </div>
      </div>

      {isLoading && !summary ? (
        <div className="py-24 text-center text-foreground-muted">Đang tải dữ liệu thống kê...</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <KpiCard icon={<IconPayments />} label="Tổng doanh thu" value={summary ? formatPriceVnd(summary.total_revenue) : "-"} />
          </div>
          <KpiCard icon={<IconCart />} label="Tổng đơn hàng" value={summary ? String(summary.total_orders) : "-"} />
          <KpiCard icon={<IconUserAdd />} label="Khách hàng mới" value={summary ? String(summary.new_users) : "-"} />

          <div className="rounded-xl bg-surface p-6 md:col-span-3">
            <h3 className="mb-6 font-heading text-xl text-foreground">Doanh thu theo ngày</h3>
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
