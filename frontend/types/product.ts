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

// Khớp `ProductCreate` thật (backend/app/schemas/product.py, task 3.4.1) -
// `slug` cố tình KHÔNG có ở đây (task 4.4.1 - Admin không nhập tay, luôn để
// Backend tự sinh từ `name`, xem giải thích ở CLAUDE.md mục Admin/Product).
// `price` là string (input dạng text/number chuyển sang string trước khi
// gửi) - cùng lý do Product.price, Backend nhận Decimal qua Pydantic.
export interface ProductCreatePayload {
  category_id: number;
  name: string;
  description?: string;
  price: string;
  // Optional - form Admin (task 4.4.1) KHÔNG có field tồn kho (đúng quyết
  // định 3.4.1, xem ProductUpdatePayload bên dưới) nên không gửi field này
  // lúc tạo, để Backend tự áp dụng default=0 (ProductCreate.stock_quantity).
  stock_quantity?: number;
}

// Khớp `ProductUpdate` thật - TOÀN BỘ field optional (partial update, field
// không truyền = giữ nguyên ở Backend, `exclude_unset`). CỐ TÌNH KHÔNG có
// `stock_quantity` (Backend cũng không nhận field này qua PUT - xem docstring
// `ProductUpdate` gốc: rủi ro "lost update" với giao dịch checkout đang trừ
// kho tương đối cùng lúc, cần cơ chế riêng nhận DELTA, chưa làm - task 8.2).
export interface ProductUpdatePayload {
  category_id?: number;
  name?: string;
  description?: string;
  price?: string;
  is_active?: boolean;
}
