"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { ProductFormModal } from "@/components/admin/ProductFormModal";
import { ProductTable } from "@/components/admin/ProductTable";
import { api } from "@/lib/axios";
import type { Category } from "@/types/category";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

const SEARCH_DEBOUNCE_MS = 450;

/**
 * Client Component (task 4.4.1) - CSR, cùng lý do `/orders` (task 4.3.3):
 * trang quản trị nội bộ, cần tương tác nhiều (search/filter/CRUD ngay không
 * reload) hơn là cần SEO. State filter (search/category/is_active/page) giữ
 * ở `useState` THƯỜNG, KHÔNG đồng bộ 2 CHIỀU qua URL `searchParams` như
 * `ProductFilters` (Customer catalog) - quyết định đơn giản hóa có chủ đích
 * VẪN GIỮ NGUYÊN: đây là phiên làm việc nội bộ của Admin, không cần share
 * link/bookmark theo bộ lọc như trang khách hàng.
 *
 * NGOẠI LỆ DUY NHẤT (task "Hoàn thiện quản trị sản phẩm, danh mục và kho"):
 * đọc `?product_id=` MỘT CHIỀU lúc mount (KHÔNG ghi ngược lại URL khi Admin
 * tự đổi filter sau đó) - phục vụ link "tới sản phẩm" từ trang lịch sử kho
 * (`/admin/inventory`), lọc CHÍNH XÁC đúng 1 sản phẩm qua `GET
 * /products/admin?product_id=` (thấy được cả sản phẩm đã ẩn, khác trang chi
 * tiết public). Cần bọc `<Suspense>` vì dùng `useSearchParams()` (Next.js App
 * Router bắt buộc, đã tự gặp lỗi build thiếu Suspense ở `/orders`, task 4.3.3).
 *
 * Gọi `GET /products/admin` (task 4.4.1, KHÔNG PHẢI `GET /products` public)
 * - endpoint duy nhất cho phép Admin thấy sản phẩm `is_active=False`.
 */
export default function AdminProductsPage() {
  return (
    <Suspense fallback={null}>
      <AdminProductsPageContent />
    </Suspense>
  );
}

function AdminProductsPageContent() {
  const searchParams = useSearchParams();
  const initialProductId = searchParams.get("product_id");

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [isActive, setIsActive] = useState("");
  const [productId, setProductId] = useState(initialProductId ?? "");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const fetchProducts = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 10 };
      if (search) params.search = search;
      if (categoryId) params.category_id = categoryId;
      if (isActive) params.is_active = isActive;
      if (productId) params.product_id = productId;
      const { data } = await api.get<ApiResponse<PaginatedResponse<Product>>>("/products/admin", { params });
      setProducts(data.data.items);
      setTotalPages(data.data.total_pages);
      setTotal(data.data.total);
      setPageSize(data.data.page_size);
    } catch {
      toast.error("Không tải được danh sách sản phẩm.");
    } finally {
      setIsLoading(false);
    }
  }, [page, search, categoryId, isActive, productId]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  useEffect(() => {
    api
      .get<ApiResponse<Category[]>>("/categories")
      .then(({ data }) => setCategories(data.data))
      .catch(() => {});
  }, []);

  // Debounce search - chờ ngừng gõ mới trigger refetch (cùng pattern
  // ProductFilters, task 4.2.3), luôn quay về trang 1 khi đổi từ khóa.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function handleCategoryChange(value: string) {
    setCategoryId(value);
    setPage(1);
  }

  function handleIsActiveChange(value: string) {
    setIsActive(value);
    setPage(1);
  }

  function clearProductIdFilter() {
    setProductId("");
    setPage(1);
  }

  function openCreateModal() {
    setEditingProduct(null);
    setIsModalOpen(true);
  }

  function openEditModal(product: Product) {
    setEditingProduct(product);
    setIsModalOpen(true);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-heading text-2xl text-foreground">Quản lý sản phẩm</h1>
          <p className="mt-1 text-sm text-foreground-muted">Quản lý danh mục, giá cả và tồn kho của bạn.</p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-background hover:bg-primary-hover"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
          Thêm sản phẩm
        </button>
      </div>

      {productId && (
        <div className="flex items-center justify-between rounded-lg border border-primary-300 bg-primary-100 px-4 py-2 text-sm text-primary-800">
          <span>Đang lọc theo đúng 1 sản phẩm (mở từ trang lịch sử kho).</span>
          <button type="button" onClick={clearProductIdFilter} className="font-semibold underline">
            Bỏ lọc, xem toàn bộ
          </button>
        </div>
      )}

      <ProductTable
        products={products}
        isLoading={isLoading}
        search={searchInput}
        onSearchChange={setSearchInput}
        categoryId={categoryId}
        onCategoryChange={handleCategoryChange}
        categories={categories}
        isActive={isActive}
        onIsActiveChange={handleIsActiveChange}
        page={page}
        totalPages={totalPages}
        total={total}
        pageSize={pageSize}
        onPageChange={setPage}
        onEdit={openEditModal}
        onChanged={fetchProducts}
      />

      <ProductFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        product={editingProduct}
        categories={categories}
        onSaved={fetchProducts}
      />
    </div>
  );
}
