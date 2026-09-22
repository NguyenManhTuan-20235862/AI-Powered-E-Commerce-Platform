export type InventoryReason = "restock" | "damage" | "audit";
export interface InventoryProduct {
  id: number;
  name: string;
  stock_quantity: number;
  image_url: string | null;
  is_active: boolean;
}
export interface InventoryAdjustment {
  id: number;
  product_id: number;
  product_name: string;
  change_quantity: number;
  stock_before: number;
  stock_after: number;
  reason: InventoryReason;
  note: string | null;
  admin_id: number;
  created_at: string;
}
export const inventoryReasons: Record<InventoryReason, string> = {
  restock: "Nhập kho", damage: "Hàng hỏng", audit: "Chênh lệch kiểm kê",
};
