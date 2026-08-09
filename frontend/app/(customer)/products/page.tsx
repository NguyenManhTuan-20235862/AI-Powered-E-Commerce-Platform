import Link from "next/link";

import { ProductFilters } from "@/components/product/ProductFilters";
import { ProductGrid } from "@/components/product/ProductGrid";
import { SortDropdown } from "@/components/product/SortDropdown";
import { fetchApi } from "@/lib/api-server";
import type { Category } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

// 12 (3 cột x 4 hàng ở desktop) - khớp bố cục lưới đã thiết kế (Stitch), thay
// vì mặc định 20 của Backend (PaginationParams.page_size).
const PAGE_SIZE = 12;

type SearchParams = Record<string, string | string[] | undefined>;

function getParam(searchParams: SearchParams, key: string): string | undefined {
  const value = searchParams[key];
  return Array.isArray(value) ? value[0] : value;
}

function buildProductsQuery(searchParams: SearchParams): URLSearchParams {
  const params = new URLSearchParams();
  params.set("page_size", String(PAGE_SIZE));

  const page = getParam(searchParams, "page");
  if (page) params.set("page", page);

  const category = getParam(searchParams, "category");
  if (category) params.set("category_id", category);

  const minPrice = getParam(searchParams, "min_price");
  if (minPrice) params.set("min_price", minPrice);

  const maxPrice = getParam(searchParams, "max_price");
  if (maxPrice) params.set("max_price", maxPrice);

  const inStock = getParam(searchParams, "in_stock");
  if (inStock === "1") params.set("in_stock", "true");

  const sortBy = getParam(searchParams, "sort_by");
  if (sortBy) params.set("sort_by", sortBy);

  // task 4.2.3 - Backend đã hỗ trợ search từ task 3.4.1 (ILIKE theo tên),
  // trước đó Frontend chưa có ô nhập nên chưa từng truyền param này.
  const search = getParam(searchParams, "search");
  if (search) params.set("search", search);

  return params;
}

// Query string cho link phân trang - GIỮ NGUYÊN mọi filter/sort hiện tại,
// chỉ đổi "page" (Next.js Link SSR-native, không cần client state để
// "nhớ" filter đang chọn - toàn bộ nằm trong URL).
function buildPageHref(searchParams: SearchParams, page: number): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (key === "page" || value === undefined) continue;
    params.set(key, Array.isArray(value) ? value[0] : value);
  }
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/products?${query}` : "/products";
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const resolvedSearchParams = await searchParams;
  const productsQuery = buildProductsQuery(resolvedSearchParams);

  let productsData: PaginatedResponse<Product> | null = null;
  let categories: Category[] = [];
  let loadError = false;

  try {
    [productsData, categories] = await Promise.all([
      fetchApi<PaginatedResponse<Product>>("/products", productsQuery),
      fetchApi<Category[]>("/categories"),
    ]);
  } catch {
    loadError = true;
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 md:flex-row">
      <ProductFilters categories={categories} />

      <section className="flex w-full flex-col gap-4 md:w-3/4">
        {loadError || !productsData ? (
          <div className="rounded-2xl bg-surface p-8 text-center">
            <p className="font-heading text-lg text-foreground">Không tải được danh sách sản phẩm</p>
            <p className="mt-1 text-sm text-foreground-muted">Vui lòng thử lại sau.</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col items-start justify-between gap-3 rounded-lg bg-surface p-3 sm:flex-row sm:items-center">
              <p className="text-sm text-foreground-secondary">
                Hiển thị <span className="font-bold text-foreground">{productsData.items.length}</span> trên{" "}
                <span className="font-bold text-foreground">{productsData.total}</span> sản phẩm
              </p>
              <SortDropdown />
            </div>

            <ProductGrid products={productsData.items} />

            {productsData.total_pages > 1 && (
              <div className="mt-4 flex items-center justify-center gap-3">
                <Link
                  href={buildPageHref(resolvedSearchParams, Math.max(1, productsData.page - 1))}
                  aria-disabled={productsData.page <= 1}
                  className={`rounded-md border border-primary px-4 py-2 text-sm text-primary transition-colors hover:bg-primary hover:text-background ${
                    productsData.page <= 1 ? "pointer-events-none opacity-40" : ""
                  }`}
                >
                  Trước
                </Link>
                <span className="text-sm text-foreground-secondary">
                  Trang {productsData.page} / {productsData.total_pages}
                </span>
                <Link
                  href={buildPageHref(resolvedSearchParams, Math.min(productsData.total_pages, productsData.page + 1))}
                  aria-disabled={productsData.page >= productsData.total_pages}
                  className={`rounded-md border border-primary px-4 py-2 text-sm text-primary transition-colors hover:bg-primary hover:text-background ${
                    productsData.page >= productsData.total_pages ? "pointer-events-none opacity-40" : ""
                  }`}
                >
                  Sau
                </Link>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
