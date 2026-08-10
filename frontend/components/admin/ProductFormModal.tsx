"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { resolveProductImageUrlClient } from "@/lib/format";
import { productFormSchema, type ProductFormValues } from "@/lib/validations/product";
import type { Category } from "@/types/category";
import type { ApiResponse } from "@/types/common";
import type { Product, ProductCreatePayload, ProductUpdatePayload } from "@/types/product";

/**
 * Client Component (task 4.4.1) - modal thêm/sửa sản phẩm, react-hook-form +
 * zod (cùng pattern CheckoutForm/LoginForm). Port từ thiết kế Stitch
 * `stitch_vun_admin_product_manager/code.html` - toggle "Trạng thái hiển
 * thị" dùng checkbox thật (`peer` + `after:`, KHÔNG PHẢI button tự quản lý
 * translate như `ProductFilters.tsx`) - vị trí nghỉ `after:left-0.5` LUÔN có
 * mặt vô điều kiện (không nằm trong nhánh ternary có thể quên), tránh đúng
 * lớp bug "knob lệch phải" đã tự gặp trước đó - đồng thời khớp tự nhiên với
 * `register()` của react-hook-form cho checkbox (không cần state boolean
 * riêng để đồng bộ).
 *
 * KHÔNG có field `stock_quantity`/`slug` trong form - xem giải thích ở
 * `lib/validations/product.ts`.
 *
 * Luồng ảnh: `POST /products/{id}/image` BẮT BUỘC có `id` sản phẩm đã tồn
 * tại - lúc TẠO MỚI, phải `POST /products` trước để có `id` thật rồi mới
 * upload ảnh (2 request tuần tự phía sau 1 nút "Lưu" duy nhất, Admin không
 * thấy sự khác biệt 2 bước). Nếu upload ảnh lỗi sau khi sản phẩm đã tạo
 * thành công, KHÔNG rollback sản phẩm (đã tồn tại thật) - chỉ báo lỗi riêng,
 * Admin có thể sửa lại để thêm ảnh sau.
 */
export function ProductFormModal({
  isOpen,
  onClose,
  product,
  categories,
  onSaved,
}: {
  isOpen: boolean;
  onClose: () => void;
  product: Product | null;
  categories: Category[];
  onSaved: () => void;
}) {
  const isEditMode = product !== null;
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormValues>({ resolver: zodResolver(productFormSchema) });

  useEffect(() => {
    if (!isOpen) return;
    setImageFile(null);
    if (product) {
      reset({
        name: product.name,
        category_id: String(product.category.id),
        price: product.price,
        description: product.description ?? "",
        is_active: product.is_active,
      });
      setImagePreview(resolveProductImageUrlClient(product.image_url));
    } else {
      reset({ name: "", category_id: "", price: "", description: "", is_active: true });
      setImagePreview(null);
    }
  }, [isOpen, product, reset]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  }

  async function uploadImageIfNeeded(productId: number) {
    if (!imageFile) return;
    const formData = new FormData();
    formData.append("file", imageFile);
    try {
      await api.post(`/products/${productId}/image`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Upload ảnh thất bại - có thể sửa lại sản phẩm để thử lại."));
    }
  }

  async function onSubmit(values: ProductFormValues) {
    try {
      if (isEditMode) {
        const payload: ProductUpdatePayload = {
          name: values.name,
          category_id: Number(values.category_id),
          price: values.price,
          description: values.description || undefined,
          is_active: values.is_active,
        };
        await api.put<ApiResponse<Product>>(`/products/${product.id}`, payload);
        await uploadImageIfNeeded(product.id);
        toast.success("Đã cập nhật sản phẩm");
      } else {
        const payload: ProductCreatePayload = {
          name: values.name,
          category_id: Number(values.category_id),
          price: values.price,
          description: values.description || undefined,
        };
        const { data } = await api.post<ApiResponse<Product>>("/products", payload);
        const newProduct = data.data;
        // Backend luôn tạo sản phẩm mới với is_active=True (products.is_active
        // model default) - nếu Admin bỏ chọn "Trạng thái hiển thị" ngay lúc
        // tạo, cần 1 PUT riêng để tắt (POST /products không nhận is_active).
        if (!values.is_active) {
          await api.put(`/products/${newProduct.id}`, { is_active: false });
        }
        await uploadImageIfNeeded(newProduct.id);
        toast.success("Đã tạo sản phẩm mới");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(extractApiErrorMessage(err, "Lưu sản phẩm thất bại. Vui lòng thử lại."));
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-foreground/40 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div className="relative flex max-h-[90vh] w-full max-w-xl flex-col rounded-xl border border-border bg-surface shadow-warm">
        <div className="flex items-center justify-between border-b border-border p-5">
          <h2 className="font-heading text-lg text-foreground">{isEditMode ? "Sửa sản phẩm" : "Thêm sản phẩm mới"}</h2>
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
          id="product-form"
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4 overflow-y-auto p-5"
          noValidate
        >
          <div className="flex gap-4">
            <div className="w-1/3 shrink-0">
              <label className="mb-1 block text-sm font-semibold text-foreground-secondary">Ảnh sản phẩm</label>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex h-32 w-full flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-border bg-background text-foreground-muted transition-colors hover:border-primary hover:text-primary"
              >
                {imagePreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imagePreview} alt="Xem trước" className="h-full w-full object-cover" />
                ) : (
                  <>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <circle cx="9" cy="9" r="2" />
                      <path d="M21 15l-5-5L5 21" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="mt-1 text-xs">Tải ảnh lên</span>
                  </>
                )}
              </button>
              <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </div>

            <div className="flex flex-1 flex-col gap-3">
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-semibold text-foreground-secondary">
                  Tên sản phẩm *
                </label>
                <input
                  id="name"
                  type="text"
                  placeholder="Nhập tên sản phẩm"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  {...register("name")}
                />
                {errors.name && <p className="mt-1 text-xs text-error">{errors.name.message}</p>}
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label htmlFor="category_id" className="mb-1 block text-sm font-semibold text-foreground-secondary">
                    Danh mục
                  </label>
                  <select
                    id="category_id"
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    {...register("category_id")}
                  >
                    <option value="">Chọn danh mục</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  {errors.category_id && <p className="mt-1 text-xs text-error">{errors.category_id.message}</p>}
                </div>
                <div className="flex-1">
                  <label htmlFor="price" className="mb-1 block text-sm font-semibold text-foreground-secondary">
                    Giá (₫) *
                  </label>
                  <input
                    id="price"
                    type="number"
                    min={0}
                    placeholder="0"
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    {...register("price")}
                  />
                  {errors.price && <p className="mt-1 text-xs text-error">{errors.price.message}</p>}
                </div>
              </div>
            </div>
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-semibold text-foreground-secondary">
              Mô tả
            </label>
            <textarea
              id="description"
              rows={3}
              placeholder="Nhập mô tả sản phẩm..."
              className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              {...register("description")}
            />
            {errors.description && <p className="mt-1 text-xs text-error">{errors.description.message}</p>}
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border bg-background p-4">
            <div>
              <span className="block text-sm font-semibold text-foreground">Trạng thái hiển thị</span>
              <span className="block text-xs text-foreground-muted">Sản phẩm sẽ hiển thị ngay lập tức nếu bật.</span>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input type="checkbox" className="peer sr-only" {...register("is_active")} />
              <div className="peer relative h-6 w-11 rounded-full bg-background transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:border after:border-border after:bg-white after:transition-transform after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-[22px]" />
            </label>
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
            form="product-form"
            disabled={isSubmitting}
            className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-background hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Đang lưu..." : "Lưu sản phẩm"}
          </button>
        </div>
      </div>
    </div>
  );
}
