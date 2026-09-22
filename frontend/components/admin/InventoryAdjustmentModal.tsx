"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/axios";
import { extractApiErrorMessage } from "@/lib/api-error";
import type { ApiResponse } from "@/types/common";
import { inventoryReasons, type InventoryAdjustment, type InventoryProduct, type InventoryReason } from "@/types/inventory";

export function InventoryAdjustmentModal({ product, onClose, onSaved }: {
  product: InventoryProduct; onClose: () => void; onSaved: (result: InventoryAdjustment) => void;
}) {
  const [reason, setReason] = useState<InventoryReason>("restock");
  const [direction, setDirection] = useState(1);
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const attempt = useRef<{ payload: string; key: string } | null>(null);
  const change = Number(quantity) * (reason === "restock" ? 1 : reason === "damage" ? -1 : direction);
  const valid = Number.isInteger(Number(quantity)) && Number(quantity) > 0 && Number(quantity) <= 2147483647 && note.length <= 500;
  const inputClass = "w-full rounded-lg border border-border bg-background px-3 py-2";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy.current || !valid) return;
    if (!confirmed) { setConfirmed(true); return; }
    const payload = { product_id: product.id, change_quantity: change, reason, note: note || null };
    const fingerprint = JSON.stringify(payload);
    if (attempt.current?.payload !== fingerprint) attempt.current = { payload: fingerprint, key: crypto.randomUUID() };
    busy.current = true;
    setPending(true);
    setError("");
    try {
      const { data } = await api.post<ApiResponse<InventoryAdjustment>>("/admin/inventory/adjust", payload, {
        headers: { "Idempotency-Key": attempt.current.key },
      });
      toast.success(`Đã điều chỉnh kho: ${data.data.stock_before} → ${data.data.stock_after}`);
      onSaved(data.data);
      onClose();
    } catch (err) {
      setError(extractApiErrorMessage(err, "Chưa nhận được kết quả. Hãy thử lại cùng thao tác."));
    } finally { busy.current = false; setPending(false); }
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
    <form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="inventory-title" className="w-full max-w-lg space-y-4 rounded-2xl bg-surface p-6 shadow-warm">
      <h2 id="inventory-title" className="font-heading text-xl">Điều chỉnh kho</h2>
      <p>{product.name} · Tồn hiện tại: {product.stock_quantity}</p>
      <fieldset disabled={pending || confirmed} className="space-y-3">
        <label className="block">Lý do<select className={inputClass} value={reason} onChange={e => setReason(e.target.value as InventoryReason)}>
          {Object.entries(inventoryReasons).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
        {reason === "audit" && <label className="block">Hướng điều chỉnh<select className={inputClass} value={direction} onChange={e => setDirection(Number(e.target.value))}><option value={1}>Tăng</option><option value={-1}>Giảm</option></select></label>}
        <label className="block">Số lượng<input required type="number" min={1} max={2147483647} step={1} className={inputClass} value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
        <label className="block">Ghi chú<textarea maxLength={500} className={inputClass} value={note} onChange={e => setNote(e.target.value)} /></label>
      </fieldset>
      <p className="text-sm text-foreground-muted">Kiểm kê cộng/trừ phần chênh lệch, không đặt lại tổng tồn kho. Tồn dự kiến: {valid ? product.stock_quantity + change : "—"}. Tồn thực tế có thể thay đổi do đặt hàng.</p>
      {confirmed && <p className="rounded-lg bg-primary-100 p-3">Xác nhận {change > 0 ? "tăng" : "giảm"} {Math.abs(change)} sản phẩm — {inventoryReasons[reason]}.</p>}
      {error && <p role="alert" className="text-error">{error}</p>}
      <div className="flex justify-end gap-3">
        <button type="button" disabled={pending} onClick={onClose} className="rounded-lg border border-border px-4 py-2">Đóng</button>
        {confirmed && !attempt.current && <button type="button" onClick={() => setConfirmed(false)}>Sửa lại</button>}
        <button disabled={pending || !valid} className="rounded-lg bg-primary px-4 py-2 text-white disabled:opacity-50">{pending ? "Đang xử lý…" : confirmed ? "Xác nhận điều chỉnh" : "Xem lại điều chỉnh"}</button>
      </div>
    </form>
  </div>;
}
