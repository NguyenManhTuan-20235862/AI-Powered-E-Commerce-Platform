// Khớp CHÍNH XÁC `ReviewRead` thật (backend/app/schemas/review.py, task
// "Hoàn thiện review sản phẩm") - `id` là ObjectId Mongo dạng string (KHÔNG
// PHẢI số như mọi resource MySQL khác trong dự án - CartItem/Order/Product
// đều dùng id số). Router trả "id" (KHÔNG PHẢI "_id") ra JSON công khai
// (`response_model_by_alias=False`) - không rò rỉ quy ước nội bộ MongoDB.

export interface Review {
  id: string;
  product_id: number;
  user_id: number;
  user_name: string;
  order_id: number;
  rating: number;
  comment: string | null;
  images: string[] | null;
  is_verified_purchase: boolean;
  created_at: string;
  updated_at: string | null;
}

// Khớp `ReviewListRead` (response GET /products/{id}/reviews) - phân trang
// RIÊNG (KHÔNG dùng chung `PaginatedResponse<T>` ở types/common.ts) vì có
// thêm `average_rating`, xem docstring backend.
export interface ReviewListResponse {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  average_rating: number | null;
}

// Payload POST /products/{id}/reviews - khớp `ReviewCreateRequest` thật.
// `order_id` do CLIENT chỉ định (user tự chọn đơn hàng nào trong số các đơn
// `delivered` chứa đúng sản phẩm này để gắn review vào).
export interface ReviewCreatePayload {
  order_id: number;
  rating: number;
  comment?: string;
}

// Khớp `ReviewAdminRead` (response GET /reviews, Admin) - CÓ `is_deleted` +
// `product_name` (join thời điểm đọc, KHÔNG có trong `Review` công khai).
export interface AdminReview extends Review {
  is_deleted: boolean;
  product_name: string | null;
}
