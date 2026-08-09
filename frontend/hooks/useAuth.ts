"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/axios";
import { clearTokens, getToken, isTokenExpired, removeToken } from "@/lib/auth";
import type { User } from "@/types/user";

// GET /auth/me trả UserResponse thật (snake_case full_name) - KHÔNG dùng JWT
// decode để lấy thông tin user (token chỉ có sub/role/type/jti/iat/exp, xem
// create_access_token backend/app/core/security.py) - cùng lý do LoginForm.tsx
// gọi /auth/me riêng sau khi login thay vì tin vào JWT (xem docs/KNOWN_TODOS.md #9).
type MeApiResponse = {
  success: boolean;
  message: string;
  data: { id: number; email: string; full_name: string; role: "customer" | "admin" };
};

/**
 * Custom hook đọc trạng thái đăng nhập - có token hợp lệ ở lib/auth.ts thì gọi
 * GET /auth/me lấy thông tin user thật (không tự suy ra từ JWT).
 * TODO (Thành viên B - module Auth): thay bằng React Context nếu cần chia sẻ
 * state đăng nhập giữa nhiều component mà không phải mount lại hook mỗi lần.
 */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCurrentUser = useCallback(async () => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      if (token) removeToken();
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const { data } = await api.get<MeApiResponse>("/auth/me");
      setUser({
        id: data.data.id,
        email: data.data.email,
        fullName: data.data.full_name,
        role: data.data.role,
      });
    } catch {
      // Token còn hạn theo `exp` nhưng bị Backend từ chối (đã blacklist, user
      // bị khóa is_active=False...) - coi như chưa đăng nhập, dọn token cũ.
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Best-effort - vẫn xóa token cục bộ dù gọi Backend lỗi (mất mạng, token
      // đã hết hạn/blacklist từ trước...), không chặn user đăng xuất được ở UI.
    }
    clearTokens();
    setUser(null);
  }, []);

  return {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    logout,
  };
}
