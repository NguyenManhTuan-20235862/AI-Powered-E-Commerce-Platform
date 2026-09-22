"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";

/**
 * Guard dùng chung cho route CHỈ dành cho user ĐÃ đăng nhập, không phân biệt
 * role cụ thể (`/cart`, `/checkout`, `/orders`) - cùng nguyên tắc
 * `AdminAuthGuard.tsx` (Frontend chỉ là lớp UX, Backend đã chặn thật qua
 * `require_role`/`get_current_user`) nhưng KHÔNG redirect theo role, chỉ cần
 * biết "đã đăng nhập chưa".
 *
 * Trước khi có guard này: `/cart` đọc thẳng `CartContext` (tự trả giỏ hàng
 * RỖNG khi chưa đăng nhập, KHÔNG lỗi) nên user chưa đăng nhập thấy y hệt
 * "giỏ hàng trống" thay vì bị đưa về `/login`; `/orders` gọi thẳng
 * `GET /orders` (401 nếu chưa đăng nhập) nhưng không xử lý riêng nên cũng
 * hiện nhầm "Bạn chưa có đơn hàng nào" - cả 2 đều sai UX theo yêu cầu, sửa
 * bằng 1 guard chặn TRƯỚC khi nội dung con kịp fetch/render, không phải sửa
 * riêng lẻ từng nơi.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-100 border-t-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
