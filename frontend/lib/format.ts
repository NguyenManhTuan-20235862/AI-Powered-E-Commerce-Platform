/**
 * Format giá VND kiểu Việt Nam (dấu chấm phân cách hàng nghìn, hậu tố "₫") -
 * VD "850000.00" -> "850.000 ₫". Nhận `price` dạng string (xem
 * types/product.ts) vì Backend serialize Decimal thành string, KHÔNG truyền
 * qua number trung gian bằng phép toán (chỉ dùng để hiển thị, không tính toán).
 */
export function formatPriceVnd(price: string): string {
  const value = Math.round(Number(price));
  return `${new Intl.NumberFormat("vi-VN").format(value)} ₫`;
}

// product.image_url (nếu có) là PATH TƯƠNG ĐỐI Backend trả về (VD
// "/api/v1/uploads/products/xxx.jpg", xem backend/app/core/storage.py) -
// PHẢI ghép với 1 origin gọi được Backend để dùng làm <Image> src.
//
// CHỈ dùng API_INTERNAL_URL (server-only) - KHÔNG PHẢI NEXT_PUBLIC_API_URL
// dù trực giác thường nghĩ ngược lại: next/image (components/product/
// ProductCard.tsx) KHÔNG để trình duyệt tải thẳng URL ảnh gốc - `<Image>`
// luôn render ra `<img src="/_next/image?url=...">`, và route
// `/_next/image` LUÔN tự fetch ảnh gốc ở PHÍA SERVER (bên trong container
// frontend, để resize/optimize) bất kể trang gốc là SSR hay CSR - dùng
// NEXT_PUBLIC_API_URL (localhost:8000) ở đây sẽ khiến chính SERVER Next.js
// gọi "localhost:8000" TỪ BÊN TRONG container frontend - không tới được
// container backend (đã tự gặp lỗi thật: "connect ECONNREFUSED
// 127.0.0.1:8000" lúc verify task 4.2.1). Hệ quả: hàm này CHỈ gọi an toàn
// từ Server Component (ProductCard không phải "use client") - API_INTERNAL_URL
// luôn `undefined` ở trình duyệt.
const API_ORIGIN = process.env.API_INTERNAL_URL?.replace(/\/api\/v1\/?$/, "") ?? "";

export function resolveProductImageUrl(imageUrl: string | null): string | null {
  if (!imageUrl) return null;
  if (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")) return imageUrl;
  return `${API_ORIGIN}${imageUrl}`;
}
