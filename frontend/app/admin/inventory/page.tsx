"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { InventoryAdjustmentModal } from "@/components/admin/InventoryAdjustmentModal";
import { api } from "@/lib/axios";
import { extractApiErrorMessage } from "@/lib/api-error";
import { formatPaginationRange } from "@/lib/format";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import { inventoryReasons, type InventoryAdjustment, type InventoryProduct } from "@/types/inventory";

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
  return <div className="space-y-6">
    <div className="flex items-center justify-between"><h1 className="font-heading text-2xl">Quản lý kho</h1><button className={field} onClick={() => setRevision(v => v + 1)}>Làm mới</button></div>
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
        <tbody>{data.items.map(row => "stock_quantity" in row ? <tr key={row.id} className="border-b border-border hover:bg-primary-100"><td className="p-4">#{row.id} · {row.name}</td><td>{row.stock_quantity}</td><td><button className={field} onClick={() => setSelected(row)}>Điều chỉnh kho</button></td></tr> : <tr key={row.id} className="border-b border-border"><td className="p-4">#{row.product_id} · {row.product_name}</td><td>{row.change_quantity > 0 ? "+" : ""}{row.change_quantity}</td><td>{row.stock_before} → {row.stock_after}</td><td>{inventoryReasons[row.reason]}<p className="max-w-xs break-words text-foreground-muted">{row.note}</p></td><td>#{row.admin_id}</td><td>{new Date(row.created_at).toLocaleString("vi-VN")}</td></tr>)}</tbody>
      </table></div>
      <div className="flex items-center justify-between"><span className="text-sm text-foreground-muted">Hiển thị {range.start}-{range.end} trên tổng {data.total} bản ghi</span><div className="flex gap-3"><button className={field} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Trang trước</button><span>{page}/{data.total_pages}</span><button className={field} disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Trang sau</button></div></div>
    </>}
    {selected && <InventoryAdjustmentModal product={selected} onClose={() => setSelected(null)} onSaved={() => setRevision(v => v + 1)} />}
  </div>;
}
