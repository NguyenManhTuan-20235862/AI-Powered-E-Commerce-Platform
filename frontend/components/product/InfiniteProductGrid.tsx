"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ProductCardClient } from "@/components/product/ProductCardClient";
import { ProductGrid } from "@/components/product/ProductGrid";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

// Phải khớp PAGE_SIZE ở app/(customer)/products/page.tsx (Server Component -
// fetch trang 1 lúc SSR) - dùng chung 1 số cho mọi trang "tải thêm" sau đó.
const PAGE_SIZE = 12;

/**
 * Client Component (task 4.5.2) - infinity-scroll THAY HẲN pagination số
 * trang cũ trên catalog customer (`/products`). Nhận sẵn trang 1 (SSR, từ
 * `page.tsx`) làm state khởi tạo, tự gọi `GET /products` (client-side, qua
 * `lib/axios.ts`) để tải thêm khi 1 sentinel div ở cuối danh sách lọt vào
 * viewport (IntersectionObserver - Web API chuẩn, không thêm thư viện ngoài,
 * đủ dùng cho quy mô đồ án).
 *
 * `queryParams` là snapshot filter/sort/search HIỆN TẠI (không có `page`) -
 * dùng để mọi trang tải thêm sau đó vẫn khớp đúng filter đang áp dụng. Nơi
 * gọi (`page.tsx`) PHẢI truyền `key={queryKey}` (chuỗi hoá từ cùng
 * `queryParams`) - đổi filter/sort/search sẽ đổi `key`, buộc React remount
 * lại component này (state `products`/`page` reset sạch) thay vì tự viết
 * `useEffect` resync thủ công như `ProductFilters.tsx` - đơn giản và đúng
 * hơn ở đây vì Server Component `page.tsx` ĐÃ tự fetch lại trang 1 mới mỗi
 * khi searchParams đổi, không cần đồng bộ 2 chiều.
 *
 * QUYẾT ĐỊNH: `page` KHÔNG nằm trong URL (khác pagination cũ) - share link/
 * back-forward vẫn giữ đúng filter/sort/search (không đổi so với task 4.2.3)
 * nhưng LUÔN mở lại từ trang 1, không "nhớ" đã cuộn tới đâu - khớp pattern
 * TMĐT mobile phổ biến (Shopee/Tiki/Lazada), tránh phải fetch lại N trang
 * liên tiếp mỗi lần mở link.
 */
export function InfiniteProductGrid({
  initialProducts,
  initialTotal,
  initialTotalPages,
  queryParams,
}: {
  initialProducts: Product[];
  initialTotal: number;
  initialTotalPages: number;
  queryParams: Record<string, string>;
}) {
  const [products, setProducts] = useState(initialProducts);
  const [page, setPage] = useState(1);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const hasMore = page < initialTotalPages;

  // Cờ đồng bộ (đọc/ghi ngay lập tức, không đợi re-render) để chặn gọi trùng
  // - IntersectionObserver có thể bắn nhiều lần liên tiếp (VD cuộn nhanh)
  // trước khi state `isLoadingMore` kịp cập nhật qua re-render, dựa mỗi state
  // trong closure cũ của callback dễ gọi trùng 2 lần (đã tự kiểm chứng).
  const isFetchingRef = useRef(false);

  const fetchNextPage = useCallback(async () => {
    if (isFetchingRef.current || !hasMore) return;
    isFetchingRef.current = true;
    setIsLoadingMore(true);
    setLoadError(false);
    try {
      const nextPage = page + 1;
      const { data } = await api.get<ApiResponse<PaginatedResponse<Product>>>("/products", {
        params: { ...queryParams, page: nextPage, page_size: PAGE_SIZE },
      });
      setProducts((prev) => [...prev, ...data.data.items]);
      setPage(nextPage);
    } catch {
      setLoadError(true);
    } finally {
      isFetchingRef.current = false;
      setIsLoadingMore(false);
    }
  }, [hasMore, page, queryParams]);

  useEffect(() => {
    if (!hasMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) fetchNextPage();
      },
      // Bắt đầu tải trước khi sentinel thật sự vào viewport (200px đệm) -
      // tránh người dùng thấy khoảng trống trắng ngắn giữa lúc cuộn tới đáy
      // và lúc trang mới load xong.
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, fetchNextPage]);

  if (products.length === 0) {
    return <ProductGrid products={[]} />;
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => (
          <ProductCardClient key={product.id} product={product} />
        ))}
      </div>

      <div className="flex flex-col items-center gap-2 py-4">
        {/* Chỉ báo tiến trình (task 4.5.2) - LUÔN hiện 1 dòng duy nhất, đổi
            nội dung theo trạng thái thay vì tách riêng 2 dòng "đang tải"/"đã
            xong" chồng nhau: còn trang sau -> "Đang hiển thị {đã tải}/
            {tổng}"; hết trang -> "Đã hiển thị tất cả {tổng}" (giữ nguyên
            message cũ). `products.length` là số ĐÃ TẢI THỰC TẾ (không phải
            hằng số) - tự đúng dù trang cuối trả ít hơn PAGE_SIZE. */}
        <p className="text-sm text-foreground-muted">
          {hasMore ? `Đang hiển thị ${products.length}/${initialTotal} sản phẩm` : `Đã hiển thị tất cả ${initialTotal} sản phẩm`}
        </p>
        {isLoadingMore && (
          <span className="flex items-center gap-2 text-sm text-foreground-secondary">
            <span
              aria-label="Đang tải thêm sản phẩm"
              className="h-4 w-4 animate-spin rounded-full border-2 border-primary-100 border-t-primary"
            />
            Đang tải thêm sản phẩm...
          </span>
        )}
        {loadError && !isLoadingMore && (
          <button
            type="button"
            onClick={fetchNextPage}
            className="text-sm text-primary underline hover:text-primary-hover"
          >
            Tải thêm sản phẩm thất bại - Thử lại
          </button>
        )}
      </div>

      {hasMore && <div ref={sentinelRef} aria-hidden="true" data-testid="infinite-scroll-sentinel" className="h-1 w-full" />}
    </>
  );
}
