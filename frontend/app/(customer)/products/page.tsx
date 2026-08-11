import { InfiniteProductGrid } from "@/components/product/InfiniteProductGrid";
import { ProductFilters } from "@/components/product/ProductFilters";
import { SortDropdown } from "@/components/product/SortDropdown";
import { fetchApi } from "@/lib/api-server";
import type { Category } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

// 12 (3 cột x 4 hàng ở desktop) - khớp bố cục lưới đã thiết kế (Stitch), thay
// vì mặc định 20 của Backend (PaginationParams.page_size). Cũng là số lượng
// mỗi lần "tải thêm" của infinity-scroll (task 4.5.2, xem InfiniteProductGrid).
const PAGE_SIZE = 12;

type SearchParams = Record<string, string | string[] | undefined>;

function getParam(searchParams: SearchParams, key: string): string | undefined {
  const value = searchParams[key];
  return Array.isArray(value) ? value[0] : value;
}

// Snapshot filter/sort/search hiện tại dạng object phẳng (KHÔNG có `page` -
// task 4.5.2 bỏ hẳn `page` khỏi URL, xem InfiniteProductGrid) - dùng CHUNG
// cho cả (1) query SSR trang 1 và (2) truyền xuống InfiniteProductGrid (Client
// Component) làm tham số cho mọi lần "tải thêm" sau đó, đảm bảo luôn khớp
// đúng filter đang áp dụng. Trả object phẳng (không phải URLSearchParams) vì
// URLSearchParams không serialize được qua ranh giới Server -> Client Component.
function buildProductsQueryParams(searchParams: SearchParams): Record<string, string> {
  const params: Record<string, string> = {};

  const category = getParam(searchParams, "category");
  if (category) params.category_id = category;

  const minPrice = getParam(searchParams, "min_price");
  if (minPrice) params.min_price = minPrice;

  const maxPrice = getParam(searchParams, "max_price");
  if (maxPrice) params.max_price = maxPrice;

  const inStock = getParam(searchParams, "in_stock");
  if (inStock === "1") params.in_stock = "true";

  const sortBy = getParam(searchParams, "sort_by");
  if (sortBy) params.sort_by = sortBy;

  // task 4.2.3 - Backend đã hỗ trợ search từ task 3.4.1 (ILIKE theo tên),
  // trước đó Frontend chưa có ô nhập nên chưa từng truyền param này.
  const search = getParam(searchParams, "search");
  if (search) params.search = search;

  return params;
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const resolvedSearchParams = await searchParams;
  const queryParams = buildProductsQueryParams(resolvedSearchParams);
  // Key ép React remount InfiniteProductGrid mỗi khi filter/sort/search đổi -
  // xem docstring InfiniteProductGrid để biết lý do chọn remount thay vì tự
  // đồng bộ state qua useEffect.
  const queryKey = new URLSearchParams(queryParams).toString();

  const productsQuery = new URLSearchParams(queryParams);
  productsQuery.set("page_size", String(PAGE_SIZE));

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
                <span className="font-bold text-foreground">{productsData.total}</span> sản phẩm
              </p>
              <SortDropdown />
            </div>

            <InfiniteProductGrid
              key={queryKey}
              initialProducts={productsData.items}
              initialTotal={productsData.total}
              initialTotalPages={productsData.total_pages}
              queryParams={queryParams}
            />
          </>
        )}
      </section>
    </div>
  );
}
