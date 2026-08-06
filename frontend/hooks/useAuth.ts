"use client";

import { useCallback, useEffect, useState } from "react";

import { clearTokens, decodeToken, getToken, isTokenExpired, removeToken, setToken } from "@/lib/auth";
import type { User } from "@/types/user";

/**
 * Custom hook đọc/ghi trạng thái đăng nhập từ JWT lưu ở localStorage.
 * TODO (Thành viên B - module Auth): thay bằng React Context nếu cần chia sẻ
 * state đăng nhập giữa nhiều component mà không phải mount lại hook mỗi lần.
 */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (token && !isTokenExpired(token)) {
      setUser(decodeToken<User>(token));
    } else if (token) {
      removeToken();
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((token: string) => {
    setToken(token);
    setUser(decodeToken<User>(token));
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    login,
    logout,
  };
}
