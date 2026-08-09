// Khớp envelope response chuẩn của Backend (backend/app/schemas/common.py:
// APIResponse[T]/PaginatedResponse[T]) - dùng chung cho mọi domain
// (product/cart/order...), không lặp lại định nghĩa ở từng types/*.ts riêng.

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
