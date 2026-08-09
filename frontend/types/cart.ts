// Khớp CHÍNH XÁC `CartItemRead`/`CartRead` thật (backend/app/schemas/cart.py,
// task 3.4.2) - bản trước đây (productId/productName/price/imageUrl camelCase
// tùy tiện) là placeholder lệch hẳn, đã bị flag ở docs/KNOWN_TODOS.md #20.

export interface CartItem {
  id: number;
  product_id: number;
  product_name: string;
  product_slug: string;
  product_image_url: string | null;
  // string, KHÔNG PHẢI number - cùng lý do Product.price (types/product.ts):
  // Pydantic serialize Decimal thành string. Dùng lib/format.ts:formatPriceVnd().
  unit_price: string;
  quantity: number;
  subtotal: string;
  // LIVE tồn kho/trạng thái sản phẩm tại thời điểm gọi API (không phải snapshot
  // lúc thêm vào giỏ) - dùng để cảnh báo sản phẩm hết hàng/ngừng bán sau khi đã
  // có trong giỏ (xem backend/app/services/cart_service.py:get_cart()).
  stock_quantity: number;
  is_active: boolean;
}

export interface Cart {
  items: CartItem[];
  total_amount: string;
}
