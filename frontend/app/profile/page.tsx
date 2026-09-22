"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { useAuth } from "@/hooks/useAuth";

/**
 * Trang hồ sơ (`/profile`) - route TOP-LEVEL, KHÔNG nằm trong `(customer)/`
 * hay `admin/` (dùng chung cho CẢ 2 role, Customer lẫn Admin đều cần đổi
 * thông tin/mật khẩu) - tự guard trực tiếp bằng `useAuth()` thay vì
 * `AdminAuthGuard` (guard đó redirect non-admin đi chỗ khác) hay phụ thuộc
 * `CartProvider` (chỉ bọc `(customer)/`, Admin vào trang này sẽ throw nếu
 * page cố `useCart()`) - trang chỉ cần biết "đã đăng nhập chưa", không cần
 * giỏ hàng/badge Header nào cả.
 */
export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-100 border-t-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Link href={user?.role === "admin" ? "/admin/dashboard" : "/"} className="font-heading text-lg text-primary-700">
            Vun
          </Link>
          <Link href={user?.role === "admin" ? "/admin/dashboard" : "/"} className="text-sm text-foreground-secondary hover:text-foreground">
            &larr; Quay lại
          </Link>
        </div>
      </header>

      <main className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-10">
        <div>
          <h1 className="font-heading text-2xl text-foreground md:text-3xl">Hồ sơ của tôi</h1>
          <p className="mt-1 text-foreground-muted">Cập nhật thông tin cá nhân và mật khẩu đăng nhập.</p>
        </div>

        <section className="rounded-xl bg-surface p-6 shadow-warm">
          <h2 className="mb-4 font-heading text-lg text-primary">Thông tin cá nhân</h2>
          <ProfileForm />
        </section>

        <section className="rounded-xl bg-surface p-6 shadow-warm">
          <h2 className="mb-4 font-heading text-lg text-primary">Đổi mật khẩu</h2>
          <ChangePasswordForm />
        </section>
      </main>
    </div>
  );
}
