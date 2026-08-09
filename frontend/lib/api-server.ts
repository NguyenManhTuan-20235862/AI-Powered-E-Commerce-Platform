import type { ApiResponse } from "@/types/common";

// Chỉ dùng trong Server Component (SSR) - KHÔNG import file này từ Client
// Component ("use client"), API_INTERNAL_URL không có prefix NEXT_PUBLIC_
// nên process.env.API_INTERNAL_URL luôn undefined ở phía trình duyệt (xem
// docs/ENV_VARIABLES.md).
const API_INTERNAL_URL = process.env.API_INTERNAL_URL;

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
    throw new Error(`Gọi API thất bại: ${path} (status ${res.status})`);
  }
  const body: ApiResponse<T> = await res.json();
  return body.data;
}
