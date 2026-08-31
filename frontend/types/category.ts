// Khớp CHÍNH XÁC `CategoryRead` thật (backend/app/schemas/category.py) - mở
// rộng đầy đủ `slug`/`parent_id`/`created_at` (CRUD Category Admin) - bản cũ
// (task 4.2.1) chỉ có `id`/`name`/`description` vì lúc đó `GET /categories`
// là endpoint DUY NHẤT tồn tại (POST/PUT/DELETE còn 501, `CategoryRead` gốc
// cũng thiếu đúng 3 field này - xem lịch sử `backend/app/schemas/category.py`).

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  parent_id: number | null;
  created_at: string;
}

// Payload POST /categories - `slug` KHÔNG có ở đây (ẩn hoàn toàn khỏi Admin,
// Backend luôn tự sinh từ `name` - cùng quyết định đã áp dụng cho Product
// task 3.1.4, xem lib/validations/category.ts).
export interface CategoryCreatePayload {
  name: string;
  description?: string;
  parent_id?: number;
}

// KHÔNG định nghĩa bằng `Partial<CategoryCreatePayload> & {...}` - TypeScript
// GIAO (intersect) 2 kiểu `parent_id` trùng tên field thay vì cho field sau
// "đè" field trước, khiến `number | null` bị thu hẹp lại thành `number |
// undefined` (mất khả năng gửi `null` tường minh để xóa danh mục cha lúc
// PUT) - khai riêng tường minh để tránh đúng cái bẫy này.
export interface CategoryUpdatePayload {
  name?: string;
  description?: string;
  parent_id?: number | null;
}
