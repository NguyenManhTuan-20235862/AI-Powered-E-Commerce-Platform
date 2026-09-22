"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useAuthContext } from "@/context/AuthContext";
import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { profileUpdateSchema, type ProfileUpdateFormValues } from "@/lib/validations/profile";
import type { ApiResponse } from "@/types/common";

type UserApiResponse = {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  address: string | null;
  role: "customer" | "admin";
};

/**
 * Form cập nhật thông tin cá nhân (`PUT /users/me`) - cùng pattern
 * `CheckoutForm.tsx` (react-hook-form + zod, `reset()` trong `useEffect` để
 * pre-fill vì `user` từ `AuthContext` load bất đồng bộ, chưa có sẵn lúc form
 * mount). Submit xong gọi LẠI `refetch()` (AuthContext) - Header/state dùng
 * chung phải thấy tên/SĐT/địa chỉ MỚI ngay, không đợi F5 lại trang.
 */
export function ProfileForm() {
  const { user, refetch } = useAuthContext();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileUpdateFormValues>({ resolver: zodResolver(profileUpdateSchema) });

  useEffect(() => {
    if (!user) return;
    reset({
      full_name: user.fullName ?? "",
      phone: user.phone ?? "",
      address: user.address ?? "",
    });
  }, [user, reset]);

  async function onSubmit(values: ProfileUpdateFormValues) {
    setServerError(null);
    try {
      await api.put<ApiResponse<UserApiResponse>>("/users/me", {
        full_name: values.full_name,
        phone: values.phone || undefined,
        address: values.address || undefined,
      });
      await refetch();
      toast.success("Cập nhật thông tin thành công");
    } catch (err) {
      setServerError(extractApiErrorMessage(err, "Cập nhật thông tin thất bại. Vui lòng thử lại."));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1">
        <label className="text-sm font-semibold text-foreground-secondary">Email</label>
        <input
          type="email"
          value={user?.email ?? ""}
          disabled
          className="cursor-not-allowed rounded-lg border border-border bg-primary-100/40 px-4 py-3 text-foreground-muted"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="full_name" className="text-sm font-semibold text-foreground-secondary">
          Họ và tên
        </label>
        <input
          id="full_name"
          type="text"
          className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("full_name")}
        />
        {errors.full_name && <p className="text-sm text-error">{errors.full_name.message}</p>}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="phone" className="text-sm font-semibold text-foreground-secondary">
          Số điện thoại
        </label>
        <input
          id="phone"
          type="tel"
          placeholder="0912345678"
          className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("phone")}
        />
        {errors.phone && <p className="text-sm text-error">{errors.phone.message}</p>}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="address" className="text-sm font-semibold text-foreground-secondary">
          Địa chỉ
        </label>
        <textarea
          id="address"
          rows={3}
          className="resize-none rounded-lg border border-border bg-background px-4 py-3 outline-none focus:border-primary"
          {...register("address")}
        />
        {errors.address && <p className="text-sm text-error">{errors.address.message}</p>}
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
        {isSubmitting ? "Đang lưu..." : "Lưu thay đổi"}
      </button>
    </form>
  );
}
