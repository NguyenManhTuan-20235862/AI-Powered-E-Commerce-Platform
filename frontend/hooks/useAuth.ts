"use client";

import { useAuthContext } from "@/context/AuthContext";

/**
 * Đọc trạng thái đăng nhập dùng CHUNG qua `AuthContext` (đóng
 * docs/KNOWN_TODOS.md #22) - bản thân hook này giờ chỉ là 1 lớp mỏng bọc
 * `useAuthContext()`, KHÔNG tự fetch `GET /auth/me` riêng nữa. Giữ nguyên tên
 * + shape trả về ({user, isAuthenticated, isLoading, logout}) như bản cũ để
 * Header/CartContext/ChatWidget/AdminAuthGuard (đều import từ
 * "@/hooks/useAuth") không cần sửa gì - chỉ cần <AuthProvider> đã bọc ở
 * app/layout.tsx (gốc, bọc CẢ (customer) lẫn admin/) là dùng được ngay.
 */
export function useAuth() {
  const { user, isAuthenticated, isLoading, logout } = useAuthContext();
  return { user, isAuthenticated, isLoading, logout };
}
