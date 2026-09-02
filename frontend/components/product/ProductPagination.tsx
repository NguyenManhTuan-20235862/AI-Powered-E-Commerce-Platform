"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

// Số trang neo cố định ở đầu/cuối (VD [1] và [11]) - luôn hiện, bất kể trang
// hiện tại đang ở đâu.
const BOUNDARY_COUNT = 1;
// Số trang liền kề MỖI BÊN trang hiện tại (VD current=6 -> hiện 4,5,6,7,8).
const SIBLING_COUNT = 2;

export type PaginationItem = number | "ellipsis";

/**
 * Tính danh sách nút số trang cần hiện, rút gọn bằng "ellipsis" khi nhiều
 * trang - LUÔN hiện trang đầu/cuối + vài trang liền kề trang hiện tại (đúng
 * yêu cầu, KHÔNG cố định 3 trang đầu/3 trang cuối bất kể vị trí trang hiện
 * tại - hiện đúng ngữ cảnh đang xem).
 *
 * Khoảng cách giữa 2 trang liền kề trong danh sách "phải hiện":
 * - == 1: liên tục, không cần gì thêm.
 * - == 2: chỉ 1 trang bị bỏ sót - điền thẳng số đó thay vì "..." (ẩn "..."
 *   không tiết kiệm được chỗ nào so với hiện luôn số, xem test).
 * - > 2: rút gọn thật bằng "...".
 *
 * Export riêng (tách khỏi component) để test trực tiếp logic rút gọn không
 * cần render DOM.
 */
export function getPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 0) return [];

  const mustShow = new Set<number>();
  for (let p = 1; p <= BOUNDARY_COUNT; p++) mustShow.add(p);
  for (let p = totalPages - BOUNDARY_COUNT + 1; p <= totalPages; p++) mustShow.add(p);
  for (let p = currentPage - SIBLING_COUNT; p <= currentPage + SIBLING_COUNT; p++) mustShow.add(p);

  const sorted = [...mustShow].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);

  const items: PaginationItem[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0) {
      const gap = sorted[i] - sorted[i - 1];
      if (gap === 2) items.push(sorted[i] - 1);
      else if (gap > 2) items.push("ellipsis");
    }
    items.push(sorted[i]);
  }
  return items;
}

const NAV_BUTTON_CLASS =
  "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border text-foreground-secondary transition-colors hover:bg-primary-100 hover:text-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-foreground-secondary";

function FirstPageIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 17l-5-5 5-5M11 17l-5-5 5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LastPageIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 17l5-5-5-5M13 17l5-5-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * Component THUẦN, dùng chung (không gắn cứng router) - nhận `currentPage`/
 * `totalPages`/`onPageChange` qua props (cùng interface `page`/`totalPages`/
 * `onPageChange` các bảng Admin đã dùng, VD `ProductTable.tsx`) để có thể
 * tái dùng cho Admin sau này nếu cần, dù hiện tại chỉ áp dụng cho catalog
 * Customer (qua `ProductPaginationUrlSync` bên dưới - bọc URL-sync riêng,
 * KHÔNG trộn vào component thuần này).
 *
 * 4 nút điều hướng (<<, <, >, >>) + số trang rút gọn bằng "...". Touch
 * target tối thiểu 40x40px (task 4.5.1) - `h-10 w-10` = đúng 40px. Trạng
 * thái: Active (`bg-primary text-background`, đúng token "trạng thái
 * active" của `primary` theo DESIGN_TOKENS.md), Hover (`hover:bg-primary-100`,
 * chuẩn hover đã dùng xuyên suốt dự án), Disabled (mờ + không đổi màu hover)
 * ở << < lúc trang 1, > >> lúc trang cuối.
 */
export function ProductPagination({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const items = getPaginationItems(currentPage, totalPages);
  const isFirstPage = currentPage <= 1;
  const isLastPage = currentPage >= totalPages;

  return (
    <nav aria-label="Điều hướng trang sản phẩm" className="flex flex-wrap items-center justify-center gap-1.5">
      <button
        type="button"
        aria-label="Về trang đầu"
        onClick={() => onPageChange(1)}
        disabled={isFirstPage}
        className={NAV_BUTTON_CLASS}
      >
        <FirstPageIcon />
      </button>
      <button
        type="button"
        aria-label="Trang trước"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={isFirstPage}
        className={NAV_BUTTON_CLASS}
      >
        <ChevronLeftIcon />
      </button>

      {items.map((item, index) =>
        item === "ellipsis" ? (
          <span
            key={`ellipsis-${index}`}
            aria-hidden="true"
            className="flex h-10 w-10 shrink-0 items-center justify-center text-foreground-muted"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            aria-label={`Trang ${item}`}
            aria-current={item === currentPage ? "page" : undefined}
            onClick={() => onPageChange(item)}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
              item === currentPage
                ? "bg-primary text-background"
                : "text-foreground-secondary hover:bg-primary-100 hover:text-primary"
            }`}
          >
            {item}
          </button>
        ),
      )}

      <button
        type="button"
        aria-label="Trang sau"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={isLastPage}
        className={NAV_BUTTON_CLASS}
      >
        <ChevronRightIcon />
      </button>
      <button
        type="button"
        aria-label="Đến trang cuối"
        onClick={() => onPageChange(totalPages)}
        disabled={isLastPage}
        className={NAV_BUTTON_CLASS}
      >
        <LastPageIcon />
      </button>
    </nav>
  );
}

/**
 * Bọc `ProductPagination` cho catalog Customer - đọc/ghi `?page=` qua URL
 * (KHÁC Admin dùng `useState` cục bộ) + cuộn mượt về đầu lưới sản phẩm khi
 * đổi trang (yêu cầu #6 - tìm phần tử qua `id="product-grid-top"`, KHÔNG
 * cuộn về đầu trang toàn bộ để giữ Header/sidebar filter nguyên vị trí).
 * Tách riêng khỏi `ProductPagination` (component thuần ở trên) để giữ
 * component đó KHÔNG gắn cứng router - tái dùng được cho Admin sau này.
 *
 * `currentPage`/`totalPages` nhận qua props từ Server Component `page.tsx`
 * (giá trị THẬT Backend đã trả về, KHÔNG tự parse lại `useSearchParams()` -
 * tránh lệch nếu Backend áp dụng logic khác cách parse phía Client, VD giá
 * trị `page` không hợp lệ).
 */
export function ProductPaginationUrlSync({
  currentPage,
  totalPages,
}: {
  currentPage: number;
  totalPages: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function handlePageChange(page: number) {
    const params = new URLSearchParams(searchParams.toString());
    if (page <= 1) params.delete("page");
    else params.set("page", String(page));
    startTransition(() => {
      router.push(`/products?${params.toString()}`);
    });
    document.getElementById("product-grid-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className={`flex justify-center ${isPending ? "opacity-60" : ""}`}>
      <ProductPagination currentPage={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}
