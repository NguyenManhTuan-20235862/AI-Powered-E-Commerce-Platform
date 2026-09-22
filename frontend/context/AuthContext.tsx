"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/axios";
import { clearTokens, getRefreshToken, getToken } from "@/lib/auth";
import type { User } from "@/types/user";

// GET /auth/me trả UserResponse thật (snake_case full_name) - KHÔNG dùng JWT
// decode để lấy thông tin user (token chỉ có sub/role/type/jti/iat/exp, xem
// create_access_token backend/app/core/security.py) - cùng lý do LoginForm.tsx
// gọi lại state này ngay sau khi login thay vì tin vào JWT (xem docs/KNOWN_TODOS.md #9).
type MeApiResponse = {
  success: boolean;
  message: string;
  data: {
    id: number;
    email: string;
    full_name: string;
    phone: string | null;
    address: string | null;
    role: "customer" | "admin";
  };
};

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  logout: () => Promise<void>;
  /** Gọi lại `GET /auth/me` ngay lập tức, trả về User vừa fetch được (hoặc
   * `null`) - dùng SAU khi login thành công (`LoginForm.tsx`) để VỪA cập nhật
   * state dùng chung NGAY (Header/Cart/ChatWidget thấy đăng nhập ngay không
   * đợi 1 vòng mount lại) VỪA lấy được `role` để quyết định redirect, KHÔNG
   * phải tự gọi `GET /auth/me` thêm 1 lần riêng (đúng thứ đang đóng lại -
   * docs/KNOWN_TODOS.md #22). */
  refetch: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapMeResponseToUser(data: MeApiResponse["data"]): User {
  return {
    id: data.id,
    email: data.email,
    fullName: data.full_name,
    phone: data.phone,
    address: data.address,
    role: data.role,
  };
}

/**
 * AuthProvider (đóng technical debt docs/KNOWN_TODOS.md #22) - state đăng
 * nhập dùng CHUNG qua React Context, đúng kiến trúc đã áp dụng cho
 * `CartContext` (task 4.3.1) - fetch `GET /auth/me` ĐÚNG 1 LẦN, mọi nơi đọc
 * qua `useAuth()` (giờ chỉ còn là `useContext()` mỏng, xem hooks/useAuth.ts)
 * thay vì mỗi component tự fetch riêng.
 *
 * Đặt ở ROOT layout (`app/layout.tsx`), KHÔNG đặt trong `(customer)/layout.tsx`
 * như `CartProvider` - khác `CartContext` (chỉ Customer cần giỏ hàng),
 * `AdminAuthGuard` (route `admin/`) CŨNG cần đọc chung state này, nên
 * `AuthProvider` phải bọc CẢ 2 route group.
 *
 * KHÔNG tự pre-check `isTokenExpired()` trước khi gọi `/auth/me` như bản cũ
 * (`hooks/useAuth.ts` trước đây) - cố tình để access token hết hạn vẫn được
 * GỌI THẬT, response interceptor (`lib/axios.ts`) tự refresh silent + retry
 * nếu refresh token còn hợp lệ (giữ đăng nhập xuyên phiên dù access token đã
 * hết hạn 60 phút) - pre-check cũ sẽ xóa token oan dù refresh token vẫn dùng
 * được, chặn mất tính năng "refresh khi access token hết hạn" ngay từ vòng
 * đầu tiên.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    if (!getToken()) {
      setUser(null);
      setIsLoading(false);
      return null;
    }
    try {
      // skipAuthRedirect: đây là lần gọi NỀN lúc mount, chạy trên MỌI trang
      // kể cả trang công khai - refresh thất bại chỉ nên âm thầm coi là chưa
      // đăng nhập (dọn token), KHÔNG điều hướng cứng sang /login (xem comment
      // đầy đủ ở lib/axios.ts) - guard thật (/cart, /checkout, /orders,
      // AdminAuthGuard) mới là nơi quyết định điều hướng.
      const { data } = await api.get<MeApiResponse>("/auth/me", { skipAuthRedirect: true });
      const nextUser = mapMeResponseToUser(data.data);
      setUser(nextUser);
      return nextUser;
    } catch {
      // Token bị từ chối (hết hạn + refresh cũng thất bại, đã blacklist, user
      // bị khóa...) - coi như chưa đăng nhập, dọn token cũ.
      clearTokens();
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const logout = useCallback(async () => {
    try {
      // Gửi kèm refresh_token trong body - Backend blacklist LUÔN (đúng
      // docs/API_SPEC.md "đưa refresh token vào Redis blacklist"), không chỉ
      // access token. refresh_token optional ở Backend nên thiếu/null vẫn ổn.
      await api.post("/auth/logout", { refresh_token: getRefreshToken() }, { skipAuthRedirect: true });
    } catch {
      // Best-effort - vẫn xóa token cục bộ dù gọi Backend lỗi (mất mạng, token
      // đã hết hạn/blacklist từ trước...), không chặn user đăng xuất được ở UI.
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      logout,
      refetch: fetchCurrentUser,
    }),
    [user, isLoading, logout, fetchCurrentUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext() phải dùng bên trong <AuthProvider>");
  return ctx;
}
