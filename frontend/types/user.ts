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
