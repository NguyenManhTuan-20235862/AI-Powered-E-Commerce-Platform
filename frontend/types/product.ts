// Khớp CHÍNH XÁC `ProductRead` thật (backend/app/schemas/product.py, task
// 3.4.1) - bản trước đây (stock/category:string/price:number) là placeholder
// lệch hẳn, cùng loại bug đã ghi ở docs/KNOWN_TODOS.md #14.

export interface CategorySummary {
  id: number;
  name: string;
}

export interface Product {
  id: number;
  category: CategorySummary;
  name: string;
  slug: string;
  description: string | null;
  // string, KHÔNG PHẢI number - Pydantic serialize Decimal thành string để
  // giữ độ chính xác tiền tệ (đã xác nhận qua backend/tests/test_product.py:
  // `data["price"] == "150000.00"`). Dùng lib/format.ts:formatPriceVnd() để
  // hiển thị, KHÔNG parseFloat() rồi làm toán tiền tệ trực tiếp.
  price: string;
  stock_quantity: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ProductSortBy = "newest" | "price_asc" | "price_desc";
