"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginFormValues } from "@/lib/validations/auth";
import { genericAuthErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { setTokens } from "@/lib/auth";
import { useAuthContext } from "@/context/AuthContext";

// POST /auth/login trả về TokenPair (access_token, refresh_token, token_type)
// - KHÔNG có object `user`/role lồng trong đó (đúng docs/API_SPEC.md mục 1) -
// khác giả định cũ (bug - xem docs/KNOWN_TODOS.md #9). Muốn biết role thật để
// redirect đúng, dùng `refetch()` của AuthContext (gọi GET /auth/me + cập
// nhật LUÔN state dùng chung - Header/Cart/ChatWidget thấy đăng nhập ngay,
// không phải tự gọi /auth/me thêm 1 lần riêng như bản cũ, đóng docs/KNOWN_TODOS.md #22).
type LoginApiResponse = {
  success: boolean;
  message: string;
  data: { access_token: string; refresh_token: string; token_type: string };
};

export function LoginForm() {
  const router = useRouter();
  const { refetch } = useAuthContext();
  const searchParams = useSearchParams();
  const justRegistered = searchParams.get("registered") === "1";
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema), mode: "onBlur" });

  async function onSubmit(values: LoginFormValues) {
    setServerError(null);
    try {
      const { data } = await api.post<LoginApiResponse>("/auth/login", {
        email: values.email,
        password: values.password,
      });
      const { access_token, refresh_token } = data.data;
      // Bảo mật: 401 ở endpoint này chỉ trả 1 message chung (xem catch) -
      // không bao giờ tiết lộ email hay password sai.
      setTokens(access_token, refresh_token, { persist: !!values.remember });

      // refetch() (AuthContext) tự gắn Authorization: Bearer từ token vừa lưu
      // ở trên (interceptor đọc getToken() mỗi request) - gọi /auth/me ngay,
      // KHÔNG cần truyền token thủ công, VÀ cập nhật state dùng chung luôn.
      const me = await refetch();
      // "/admin/dashboard" (không phải "/admin" trơ) - app/admin/ hiện KHÔNG
      // có page.tsx ở gốc (chỉ có dashboard/orders/products con), redirect
      // "/admin" sẽ 404 (đã tự kiểm chứng lúc verify task 2.3.4 fix #9) - phát
      // hiện đây là gap có sẵn từ trước, không liên quan tới bug #9 vừa sửa.
      router.push(me?.role === "admin" ? "/admin/dashboard" : "/");
    } catch (err) {
      setServerError(genericAuthErrorMessage(err, "login"));
    }
  }

  return (
    <>
      {justRegistered && !serverError && (
        <p className="auth-banner auth-banner-success">Đăng ký thành công, vui lòng đăng nhập.</p>
      )}
      {serverError && <p className="auth-banner auth-banner-error">{serverError}</p>}
      <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" className="input" placeholder="ban@email.com" autoComplete="email" {...register("email")} />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>

        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input id="password" type="password" className="input" autoComplete="current-password" {...register("password")} />
          {errors.password && <p className="field-error">{errors.password.message}</p>}
        </div>

        <div className="auth-row">
          <label className="auth-checkbox">
            <input type="checkbox" {...register("remember")} /> Ghi nhớ đăng nhập
          </label>
          <a href="#" onClick={(e) => e.preventDefault()} className="auth-link">
            Quên mật khẩu?
          </a>
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={isSubmitting}>
          {isSubmitting && <span className="auth-spinner" />}
          {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
      </form>
    </>
  );
}
