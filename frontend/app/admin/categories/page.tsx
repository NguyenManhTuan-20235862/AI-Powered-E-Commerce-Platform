"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { CategoryFormModal } from "@/components/admin/CategoryFormModal";
import { CategoryTable } from "@/components/admin/CategoryTable";
import { api } from "@/lib/axios";
import type { ApiResponse } from "@/types/common";
import type { Category } from "@/types/category";

/**
 * Client Component (CRUD Category Admin) - CSR, cùng lý do
 * `/admin/products`/`/admin/orders`/`/admin/users`: trang quản trị nội bộ,
 * không cần đồng bộ URL `searchParams`.
 *
 * `GET /categories` KHÔNG phân trang (trả TOÀN BỘ danh mục 1 lần) - chỉ 1
 * lần fetch lúc mount + sau mỗi lần CRUD (`fetchCategories` dùng CHUNG làm
 * `onSaved`/`onChanged`, không tách riêng như Product/Order/User - không có
 * state filter/trang nào phụ thuộc để phải tách).
 */
export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  const fetchCategories = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get<ApiResponse<Category[]>>("/categories");
      setCategories(data.data);
    } catch {
      toast.error("Không tải được danh sách danh mục.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  function openCreateModal() {
    setEditingCategory(null);
    setIsModalOpen(true);
  }

  function openEditModal(category: Category) {
    setEditingCategory(category);
    setIsModalOpen(true);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-heading text-2xl text-foreground">Quản lý danh mục</h1>
          <p className="mt-1 text-sm text-foreground-muted">Quản lý danh mục sản phẩm và phân cấp danh mục cha-con.</p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-background hover:bg-primary-hover"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          Thêm danh mục
        </button>
      </div>

      <CategoryTable categories={categories} isLoading={isLoading} onEdit={openEditModal} onChanged={fetchCategories} />

      <CategoryFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        category={editingCategory}
        categories={categories}
        onSaved={fetchCategories}
      />
    </div>
  );
}
