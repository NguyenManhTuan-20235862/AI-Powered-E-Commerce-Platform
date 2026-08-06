import { AuthLayout } from "@/components/auth/AuthLayout";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <AuthLayout mode="register" heading="Tạo tài khoản mới" subheading="Chỉ mất chưa đầy 1 phút để bắt đầu mua sắm cùng Vun.">
      <RegisterForm />
    </AuthLayout>
  );
}
