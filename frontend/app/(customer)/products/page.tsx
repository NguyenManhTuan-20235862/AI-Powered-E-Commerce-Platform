import { ProductFilters } from "@/components/product/ProductFilters";
import { ProductGrid } from "@/components/product/ProductGrid";
import { ProductPaginationUrlSync } from "@/components/product/ProductPagination";
import { SortDropdown } from "@/components/product/SortDropdown";
import { fetchApi } from "@/lib/api-server";
import type { Category } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

// 12 (3 cột x 4 hàng ở desktop) - khớp bố cục lưới đã thiết kế (Stitch), thay
// vì mặc định 20 của Backend (PaginationParams.page_size). Giữ nguyên số này
// từ lúc còn infinite-scroll (task 4.5.2) - chuyển sang phân trang số
// (thay thế hoàn toàn infinite-scroll) không có lý do gì để đổi.
const PAGE_SIZE = 12;

type SearchParams = Record<string, string | string[] | undefined>;

function getParam(searchParams: SearchParams, key: string): string | undefined {
  const value = searchParams[key];
  return Array.isArray(value) ? value[0] : value;
}

// Snapshot filter/sort/search hiện tại (KHÔNG gồm `page` - đọc riêng, xem
// `ProductsPage` bên dưới) dùng để build query gọi `GET /products` phía SSR.
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

  // `page` từ URL - KHÔNG hợp lệ (thiếu/NaN/<1) mặc định về 1. KHÔNG tự clamp
  // theo `total_pages` (chưa biết được trước khi gọi API) - trang vượt quá số
  // trang thật cứ gửi thẳng xuống Backend, `GET /products` trả `items` rỗng
  // (offset vượt quá dữ liệu) và `ProductGrid` đã có sẵn thông báo "Không tìm
  // thấy sản phẩm phù hợp" cho trường hợp rỗng - không cần logic riêng.
  const pageParam = getParam(resolvedSearchParams, "page");
  const page = Math.max(1, Number(pageParam) || 1);

  const productsQuery = new URLSearchParams(queryParams);
  productsQuery.set("page", String(page));
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
            {/* id neo cho cuộn mượt (ProductPaginationUrlSync) khi đổi trang -
                cuộn tới đúng đầu khu vực danh sách, KHÔNG PHẢI đầu trang toàn
                bộ (giữ Header/sidebar filter nguyên vị trí nhìn thấy). */}
            <div id="product-grid-top" className="flex flex-col items-start justify-between gap-3 rounded-lg bg-surface p-3 sm:flex-row sm:items-center">
              <p className="text-sm text-foreground-secondary">
                <span className="font-bold text-foreground">{productsData.total}</span> sản phẩm
              </p>
              <SortDropdown />
            </div>

            <ProductGrid products={productsData.items} />

            <ProductPaginationUrlSync currentPage={productsData.page} totalPages={productsData.total_pages} />
          </>
        )}
      </section>
    </div>
  );
}
