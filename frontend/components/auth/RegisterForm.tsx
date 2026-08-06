"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema, type RegisterFormValues } from "@/lib/validations/auth";
import { genericAuthErrorMessage, extractFieldError } from "@/lib/api-error";
import { api } from "@/lib/axios";

// POST /auth/register trả về user vừa tạo (UserResponse), KHÔNG có token -
// khác /auth/login (xem docs/API_SPEC.md mục 1: chỉ /auth/login "trả về
// access token + refresh token", /auth/register không có dòng tương tự).
// Đăng ký xong phải chuyển sang /login để đăng nhập thật, không tự đăng nhập
// bằng token không tồn tại (bug cũ - xem docs/KNOWN_TODOS.md #9).
type RegisterApiResponse = {
  success: boolean;
  message: string;
  data: { id: number; email: string; full_name: string; role: "customer" | "admin" };
};

export function RegisterForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema), mode: "onBlur" });

  async function onSubmit(values: RegisterFormValues) {
    setServerError(null);
    try {
      await api.post<RegisterApiResponse>("/auth/register", {
        full_name: values.full_name,
        email: values.email,
        phone: values.phone || undefined,
        password: values.password,
      });
      // Không có token để tự đăng nhập (xem giải thích ở type RegisterApiResponse
      // phía trên) - chuyển sang /login, kèm cờ báo đăng ký thành công để
      // LoginForm hiện thông báo phù hợp.
      router.push("/login?registered=1");
    } catch (err) {
      const emailError = extractFieldError(err, "email");
      if (emailError) {
        setError("email", { message: emailError }); // vd: "Email này đã được sử dụng..."
      } else {
        setServerError(genericAuthErrorMessage(err, "register"));
      }
    }
  }

  return (
    <>
      {serverError && <p className="auth-banner auth-banner-error">{serverError}</p>}
      <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
        <div className="field">
          <label htmlFor="full_name">Họ và tên</label>
          <input id="full_name" className="input" placeholder="Nguyễn Văn A" autoComplete="name" {...register("full_name")} />
          {errors.full_name && <p className="field-error">{errors.full_name.message}</p>}
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" className="input" placeholder="ban@email.com" autoComplete="email" {...register("email")} />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>

        <div className="field">
          <label htmlFor="phone">
            Số điện thoại <span className="text-muted">(không bắt buộc)</span>
          </label>
          <input id="phone" type="tel" className="input" placeholder="0912345678" autoComplete="tel" {...register("phone")} />
          {errors.phone && <p className="field-error">{errors.phone.message}</p>}
        </div>

        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input id="password" type="password" className="input" placeholder="Tối thiểu 8 ký tự" autoComplete="new-password" {...register("password")} />
          {errors.password ? (
            <p className="field-error">{errors.password.message}</p>
          ) : (
            <p className="field-hint">Tối thiểu 8 ký tự, gồm chữ hoa và số.</p>
          )}
        </div>

        <div className="field">
          <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
          <input id="confirmPassword" type="password" className="input" autoComplete="new-password" {...register("confirmPassword")} />
          {errors.confirmPassword && <p className="field-error">{errors.confirmPassword.message}</p>}
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={isSubmitting}>
          {isSubmitting && <span className="auth-spinner" />}
          {isSubmitting ? "Đang tạo tài khoản..." : "Tạo tài khoản"}
        </button>
      </form>
    </>
  );
}
