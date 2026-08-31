"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { categoryFormSchema, type CategoryFormValues } from "@/lib/validations/category";
import type { ApiResponse } from "@/types/common";
import type { Category, CategoryCreatePayload, CategoryUpdatePayload } from "@/types/category";

/**
 * Client Component (CRUD Category Admin) - modal thêm/sửa danh mục,
 * react-hook-form + zod, cùng cấu trúc `ProductFormModal.tsx` (task 4.4.1) -
 * KHÔNG qua Stitch cho trang này (đã xác nhận, cấu trúc đơn giản: bảng CRUD
 * tên/slug/mô tả/danh mục cha, không có ảnh/toggle trạng thái/tồn kho như
 * Product nên không cần thiết kế riêng).
 *
 * KHÔNG có field `slug` trong form (ẩn hoàn toàn, Backend tự sinh từ `name`)
 * - cùng quyết định UX đã áp dụng cho Product (task 3.1.4).
 *
 * Dropdown "Danh mục cha" LOẠI TRỪ chính category đang sửa khỏi danh sách
 * lựa chọn (`categories.filter(c => c.id !== category?.id)`) - chặn ngay từ
 * UI trường hợp "cha của chính mình" (vòng lặp trực tiếp) dù Backend đã tự
 * validate lại (400) - CHỈ chặn được trường hợp TRỰC TIẾP này, KHÔNG lọc
 * được vòng lặp GIÁN TIẾP (VD category đang sửa là ông/bà của 1 category
 * khác trong danh sách, chọn cháu đó làm cha) - Backend vẫn là nơi validate
 * đầy đủ cuối cùng (xem `category_service.would_create_cycle()`), lỗi 400
 * từ Backend hiện qua toast với message thật, không phải lỗi generic.
 */
export function CategoryFormModal({
  isOpen,
  onClose,
  category,
  categories,
  onSaved,
}: {
  isOpen: boolean;
  onClose: () => void;
  category: Category | null;
  categories: Category[];
  onSaved: () => void;
}) {
  const isEditMode = category !== null;
  const parentOptions = categories.filter((c) => c.id !== category?.id);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CategoryFormValues>({ resolver: zodResolver(categoryFormSchema) });

  useEffect(() => {
    if (!isOpen) return;
    if (category) {
      reset({
        name: category.name,
        description: category.description ?? "",
        parent_id: category.parent_id ? String(category.parent_id) : "",
      });
    } else {
      reset({ name: "", description: "", parent_id: "" });
    }
  }, [isOpen, category, reset]);

  async function onSubmit(values: CategoryFormValues) {
    try {
      if (isEditMode) {
        const payload: CategoryUpdatePayload = {
          name: values.name,
          description: values.description || undefined,
          parent_id: values.parent_id ? Number(values.parent_id) : null,
        };
        await api.put<ApiResponse<Category>>(`/categories/${category.id}`, payload);
        toast.success("Đã cập nhật danh mục");
      } else {
        const payload: CategoryCreatePayload = {
          name: values.name,
          description: values.description || undefined,
          parent_id: values.parent_id ? Number(values.parent_id) : undefined,
        };
        await api.post<ApiResponse<Category>>("/categories", payload);
        toast.success("Đã tạo danh mục mới");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Lưu danh mục thất bại. Vui lòng thử lại."));
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div className="relative flex max-h-[90vh] w-full max-w-lg flex-col rounded-xl border border-border bg-surface shadow-warm">
        <div className="flex items-center justify-between border-b border-border p-5">
          <h2 className="font-heading text-lg text-foreground">{isEditMode ? "Sửa danh mục" : "Thêm danh mục mới"}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="rounded-full p-1 text-foreground-muted hover:bg-primary-100 hover:text-foreground"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <form
          id="category-form"
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4 overflow-y-auto p-5"
          noValidate
        >
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-semibold text-foreground-secondary">
              Tên danh mục *
            </label>
            <input
              id="name"
              type="text"
              placeholder="Nhập tên danh mục"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              {...register("name")}
            />
            {errors.name && <p className="mt-1 text-xs text-error">{errors.name.message}</p>}
          </div>

          <div>
            <label htmlFor="parent_id" className="mb-1 block text-sm font-semibold text-foreground-secondary">
              Danh mục cha
            </label>
            <select
              id="parent_id"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              {...register("parent_id")}
            >
              <option value="">Không có</option>
              {parentOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-semibold text-foreground-secondary">
              Mô tả
            </label>
            <textarea
              id="description"
              rows={3}
              placeholder="Nhập mô tả danh mục..."
              className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              {...register("description")}
            />
            {errors.description && <p className="mt-1 text-xs text-error">{errors.description.message}</p>}
          </div>
        </form>

        <div className="flex justify-end gap-3 rounded-b-xl border-t border-border bg-background p-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-5 py-2 text-sm font-semibold text-foreground-secondary hover:bg-primary-100"
          >
            Hủy
          </button>
          <button
            type="submit"
            form="category-form"
            disabled={isSubmitting}
            className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-background hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Đang lưu..." : "Lưu danh mục"}
          </button>
        </div>
      </div>
    </div>
  );
}
