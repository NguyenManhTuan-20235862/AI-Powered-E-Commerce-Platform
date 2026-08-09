import type { ApiResponse } from "@/types/common";

// Chỉ dùng trong Server Component (SSR) - KHÔNG import file này từ Client
// Component ("use client"), API_INTERNAL_URL không có prefix NEXT_PUBLIC_
// nên process.env.API_INTERNAL_URL luôn undefined ở phía trình duyệt (xem
// docs/ENV_VARIABLES.md).
const API_INTERNAL_URL = process.env.API_INTERNAL_URL;

// task 4.2.2 - trang chi tiết sản phẩm cần phân biệt 404 (gọi notFound() của
// Next.js) với các lỗi khác (network/500 - hiện chỉ generic error) - Error
// thường không mang theo status code, nên tạo subclass riêng thay vì string
// match message (dễ vỡ nếu message đổi).
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Gọi Backend API từ Server Component. `cache: "no-store"` - trang catalog
 * dynamic theo searchParams (filter/sort/trang), tự Redis phía Backend đã lo
 * việc cache (task 3.3.1/3.4.1) - không cần thêm 1 lớp cache độc lập của
 * Next.js chồng lên, tránh 2 lớp cache lệch TTL nhau.
 */
export async function fetchApi<T>(path: string, searchParams?: URLSearchParams): Promise<T> {
  const query = searchParams?.toString();
  const url = `${API_INTERNAL_URL}${path}${query ? `?${query}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new ApiError(res.status, `Gọi API thất bại: ${path} (status ${res.status})`);
  }
  const body: ApiResponse<T> = await res.json();
  return body.data;
}
