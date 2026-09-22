"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { InventoryAdjustmentModal } from "@/components/admin/InventoryAdjustmentModal";
import { api } from "@/lib/axios";
import { extractApiErrorMessage } from "@/lib/api-error";
import { formatPaginationRange } from "@/lib/format";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import { inventoryReasons, type InventoryAdjustment, type InventoryProduct } from "@/types/inventory";

// Số dòng mỗi lần gọi API lúc export CSV (tối đa Backend cho phép, xem
// `PaginationParams.page_size`) - vòng lặp fetch HẾT các trang khớp filter
// hiện tại (KHÔNG chỉ trang 20 dòng đang hiển thị trên UI), vì "xuất CSV"
// nghĩa là xuất TOÀN BỘ kết quả lọc, không phải riêng 1 trang.
const CSV_EXPORT_PAGE_SIZE = 100;
// Giới hạn an toàn số trang tối đa fetch lúc export - chống vòng lặp vô hạn
// nếu có lỗi logic phân trang phía Backend (cùng tinh thần
// `_MAX_PARENT_CHAIN_DEPTH` phía category_service.py) - 500 trang x 100 dòng
// = 50.000 bản ghi, dư dả cho quy mô đồ án.
const CSV_EXPORT_MAX_PAGES = 500;

function escapeCsvField(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function buildCsvContent(rows: InventoryAdjustment[]): string {
  const header = ["Mã sản phẩm", "Tên sản phẩm", "Thay đổi", "Tồn trước", "Tồn sau", "Lý do", "Ghi chú", "Admin", "Thời điểm"];
  const lines = [
    header,
    ...rows.map((r) => [
      String(r.product_id),
      r.product_name,
      String(r.change_quantity),
      String(r.stock_before),
      String(r.stock_after),
      inventoryReasons[r.reason],
      r.note ?? "",
      r.admin_name,
      new Date(r.created_at).toLocaleString("vi-VN"),
    ]),
  ];
  // BOM UTF-8 (\uFEFF) ở đầu file - Excel (phổ biến nhất cho việc mở CSV
  // demo) mặc định đọc CSV theo ANSI nếu thiếu BOM, hiện sai tiếng Việt có dấu.
  return "\uFEFF" + lines.map((line) => line.map(escapeCsvField).join(",")).join("\r\n");
}

export default function InventoryPage() {
  const [tab, setTab] = useState<"low-stock" | "adjustments">("low-stock");
  const [page, setPage] = useState(1);
  const [threshold, setThreshold] = useState("10");
  const [productId, setProductId] = useState("");
  const [reason, setReason] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [data, setData] = useState<PaginatedResponse<InventoryProduct | InventoryAdjustment> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<InventoryProduct | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const params = tab === "low-stock" ? { page, page_size: 20, threshold } : {
      page, page_size: 20, product_id: productId || undefined, reason: reason || undefined,
      date_from: from || undefined, date_to: to || undefined,
    };
    api.get<ApiResponse<PaginatedResponse<InventoryProduct | InventoryAdjustment>>>(`/admin/inventory/${tab}`, { params })
      .then(response => { if (active) setData(response.data.data); })
      .catch(err => { if (active) setError(extractApiErrorMessage(err, "Không tải được dữ liệu kho.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [tab, page, threshold, productId, reason, from, to, revision]);
  const range = formatPaginationRange(page, 20, data?.total ?? 0);
  const field = "rounded-lg border border-border bg-background px-3 py-2";

  // Export CSV (task "Hoàn thiện quản trị sản phẩm, danh mục và kho") - lấy
  // TOÀN BỘ bản ghi khớp filter "Lịch sử điều chỉnh" hiện tại (KHÔNG chỉ 20
  // dòng trang đang xem), tự fetch thêm trang cho tới khi hết hoặc chạm giới
  // hạn an toàn `CSV_EXPORT_MAX_PAGES`.
  async function handleExportCsv() {
    setIsExporting(true);
    try {
      const rows: InventoryAdjustment[] = [];
      const params = {
        page_size: CSV_EXPORT_PAGE_SIZE, product_id: productId || undefined, reason: reason || undefined,
        date_from: from || undefined, date_to: to || undefined,
      };
      let exportPage = 1;
      let totalPages = 1;
      do {
        const response = await api.get<ApiResponse<PaginatedResponse<InventoryAdjustment>>>(
          "/admin/inventory/adjustments",
          { params: { ...params, page: exportPage } },
        );
        rows.push(...response.data.data.items);
        totalPages = response.data.data.total_pages;
        exportPage += 1;
      } while (exportPage <= totalPages && exportPage <= CSV_EXPORT_MAX_PAGES);

      if (rows.length === 0) {
        toast.error("Không có dữ liệu phù hợp để xuất.");
        return;
      }
      const blob = new Blob([buildCsvContent(rows)], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `lich-su-dieu-chinh-kho-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Xuất CSV thất bại. Vui lòng thử lại."));
    } finally {
      setIsExporting(false);
    }
  }

  return <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h1 className="font-heading text-2xl">Quản lý kho</h1>
      <div className="flex gap-3">
        {tab === "adjustments" && (
          <button className={field} onClick={handleExportCsv} disabled={isExporting}>
            {isExporting ? "Đang xuất..." : "Xuất CSV"}
          </button>
        )}
        <button className={field} onClick={() => setRevision(v => v + 1)}>Làm mới</button>
      </div>
    </div>
    <p className="text-sm text-foreground-muted">Lịch sử chỉ ghi điều chỉnh của Admin, không bao gồm đặt/hủy đơn. <Link href="/admin/products" className="text-primary underline">Chọn sản phẩm để điều chỉnh</Link></p>
    <div className="flex gap-3">{(["low-stock", "adjustments"] as const).map(value => <button key={value} className={`${field} ${tab === value ? "bg-primary text-white" : ""}`} onClick={() => { setTab(value); setPage(1); }}>{value === "low-stock" ? "Sắp hết hàng" : "Lịch sử điều chỉnh"}</button>)}</div>
    <div className="flex flex-wrap gap-3" onChange={() => setPage(1)}>
      {tab === "low-stock" ? <label>Ngưỡng tồn thấp <input className={field} type="number" min={1} value={threshold} onChange={e => setThreshold(e.target.value)} /></label> : <>
        <label>Mã sản phẩm <input className={field} type="number" min={1} value={productId} onChange={e => setProductId(e.target.value)} /></label>
        <label>Lý do <select className={field} value={reason} onChange={e => setReason(e.target.value)}><option value="">Tất cả</option>{Object.entries(inventoryReasons).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>Từ ngày <input className={field} type="date" value={from} onChange={e => setFrom(e.target.value)} /></label>
        <label>Đến ngày <input className={field} type="date" value={to} onChange={e => setTo(e.target.value)} /></label>
      </>}
    </div>
    {loading ? <p role="status">Đang tải…</p> : error ? <p role="alert" className="text-error">{error}</p> : !data?.items.length ? <p>Không có dữ liệu phù hợp.</p> : <>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface"><table className="w-full text-left text-sm">
        <thead><tr className="border-b border-border"><th className="p-4">Sản phẩm</th>{tab === "low-stock" ? <><th>Tồn kho</th><th>Hành động</th></> : <><th>Thay đổi</th><th>Trước → Sau</th><th>Lý do / Ghi chú</th><th>Admin</th><th>Thời điểm</th></>}</tr></thead>
        <tbody>{data.items.map(row => "stock_quantity" in row ? <tr key={row.id} className="border-b border-border hover:bg-primary-100"><td className="p-4"><Link href={`/admin/products?product_id=${row.id}`} className="text-primary underline">#{row.id} · {row.name}</Link></td><td>{row.stock_quantity}</td><td><button className={field} onClick={() => setSelected(row)}>Điều chỉnh kho</button></td></tr> : <tr key={row.id} className="border-b border-border"><td className="p-4"><Link href={`/admin/products?product_id=${row.product_id}`} className="text-primary underline">#{row.product_id} · {row.product_name}</Link></td><td>{row.change_quantity > 0 ? "+" : ""}{row.change_quantity}</td><td>{row.stock_before} → {row.stock_after}</td><td>{inventoryReasons[row.reason]}<p className="max-w-xs break-words text-foreground-muted">{row.note}</p></td><td>{row.admin_name}</td><td>{new Date(row.created_at).toLocaleString("vi-VN")}</td></tr>)}</tbody>
      </table></div>
      <div className="flex items-center justify-between"><span className="text-sm text-foreground-muted">Hiển thị {range.start}-{range.end} trên tổng {data.total} bản ghi</span><div className="flex gap-3"><button className={field} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Trang trước</button><span>{page}/{data.total_pages}</span><button className={field} disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Trang sau</button></div></div>
    </>}
    {selected && <InventoryAdjustmentModal product={selected} onClose={() => setSelected(null)} onSaved={() => setRevision(v => v + 1)} />}
  </div>;
}
