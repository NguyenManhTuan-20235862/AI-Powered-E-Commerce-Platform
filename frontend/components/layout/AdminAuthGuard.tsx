"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";

/**
 * Bảo vệ route Admin ở tầng Frontend (UX only) - Backend đã chặn thật qua
 * `require_role(Admin)` (task 1.3.3), đây chỉ tránh user thường thấy màn
 * hình Admin trống/lỗi API 403 trước khi bị đá ra. KHÔNG dùng middleware.ts:
 * Next.js Middleware chạy ở Edge/server, chỉ đọc cookie/header của request -
 * không đọc được localStorage/sessionStorage (nơi lib/auth.ts đang lưu JWT,
 * task 1.3.4), nên middleware sẽ luôn thấy "chưa đăng nhập" dù user đã login.
 *
 * Chưa đăng nhập -> "/login" (còn hành động rõ ràng: đăng nhập rồi thử lại).
 * Đã đăng nhập nhưng không phải admin -> "/" (đưa lại "/login" sẽ lặp vô ích,
 * user không có cách nào đổi role qua trang login).
 */
export function AdminAuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
    } else if (user?.role !== "admin") {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading || !isAuthenticated || user?.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-100 border-t-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
