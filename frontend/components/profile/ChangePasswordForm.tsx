"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { changePasswordSchema, type ChangePasswordFormValues } from "@/lib/validations/profile";

/**
 * Form đổi mật khẩu (`PUT /users/me/password`) - `old_password` sai trả 400
 * kèm message thật ("Mật khẩu cũ không đúng", xem
 * `app/services/user_service.py:change_password`) qua `extractApiErrorMessage()`,
 * không phải thông báo chung chung. Đổi thành công KHÔNG tự logout/xóa token
 * (access token hiện tại vẫn còn hạn dùng bình thường tới khi hết hạn tự
 * nhiên) - chỉ dọn form + toast xác nhận, cùng mức đơn giản các quyết định
 * khác trong dự án.
 */
export function ChangePasswordForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormValues>({ resolver: zodResolver(changePasswordSchema) });

  async function onSubmit(values: ChangePasswordFormValues) {
    setServerError(null);
    try {
      await api.put("/users/me/password", {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      reset();
      toast.success("Đổi mật khẩu thành công");
    } catch (err) {
      setServerError(extractApiErrorMessage(err, "Đổi mật khẩu thất bại. Vui lòng thử lại."));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1">
        <label htmlFor="old_password" className="text-sm font-semibold text-foreground-secondary">
          Mật khẩu hiện tại
        </label>
        <input
          id="old_password"
          type="password"
          autoComplete="current-password"
          className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("old_password")}
        />
        {errors.old_password && <p className="text-sm text-error">{errors.old_password.message}</p>}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="new_password" className="text-sm font-semibold text-foreground-secondary">
          Mật khẩu mới
        </label>
        <input
          id="new_password"
          type="password"
          autoComplete="new-password"
          placeholder="Tối thiểu 8 ký tự"
          className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("new_password")}
        />
        {errors.new_password && <p className="text-sm text-error">{errors.new_password.message}</p>}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="confirm_password" className="text-sm font-semibold text-foreground-secondary">
          Xác nhận mật khẩu mới
        </label>
        <input
          id="confirm_password"
          type="password"
          autoComplete="new-password"
          className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("confirm_password")}
        />
        {errors.confirm_password && <p className="text-sm text-error">{errors.confirm_password.message}</p>}
      </div>

      {serverError && (
        <p className="rounded-lg bg-error-container px-4 py-3 text-sm text-error" role="alert">
          {serverError}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-1 flex w-fit items-center justify-center rounded-2xl bg-primary px-6 py-3 font-heading text-sm text-background transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Đang đổi mật khẩu..." : "Đổi mật khẩu"}
      </button>
    </form>
  );
}
