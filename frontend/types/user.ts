export type UserRole = "customer" | "admin";

export interface User {
  id: string | number;
  email: string;
  fullName?: string;
  // task 4.3.2 - trước đó useAuth() bỏ qua 2 field này dù GET /auth/me
  // (UserResponse) đã trả về sẵn (chưa task nào cần tới) - dùng để pre-fill
  // form giao hàng ở trang checkout.
  phone?: string | null;
  address?: string | null;
  role: UserRole;
}

// Khớp CHÍNH XÁC `UserResponse` thật (backend/app/schemas/user.py) - dùng
// cho bảng Quản lý người dùng Admin (`GET /users`). KHÁC hẳn `User` ở trên
// (state user ĐANG đăng nhập qua useAuth() - cố ý camelCase + thiếu
// is_active/created_at vì use case đó không cần) - type này giữ NGUYÊN
// snake_case đúng wire format, đọc thẳng response, không qua tầng map lại
// như useAuth.ts làm.
export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  address: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
