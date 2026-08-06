import { Suspense } from "react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <AuthLayout mode="login" heading="Chào mừng trở lại" subheading="Đăng nhập để tiếp tục mua sắm tại Vun.">
      {/* LoginForm dùng useSearchParams() (đọc ?registered=1 từ RegisterForm) -
          bắt buộc bọc Suspense, nếu không `next build` lỗi lúc static render
          trang này (Next.js App Router yêu cầu Suspense boundary cho mọi
          component gọi useSearchParams). */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
