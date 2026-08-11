"use client";

import Link from "next/link";

import { AddToCartButton } from "@/components/product/AddToCartButton";
import { formatPriceVnd, resolveProductImageUrlClient } from "@/lib/format";
import type { Product } from "@/types/product";

/**
 * Client Component (task 4.5.2) - bản sao `ProductCard.tsx` dùng cho sản phẩm
 * load thêm bằng infinite-scroll (`InfiniteProductGrid.tsx`, Client Component
 * nên KHÔNG thể tái sử dụng nguyên `ProductCard` gốc). KHÁC DUY NHẤT: dùng
 * `<img>` + `resolveProductImageUrlClient()` (NEXT_PUBLIC_API_URL) thay vì
 * `next/image` + `resolveProductImageUrl()` (API_INTERNAL_URL, server-only) -
 * route `/_next/image` luôn fetch ảnh gốc Ở PHÍA SERVER, `API_INTERNAL_URL`
 * luôn `undefined` ở trình duyệt nên sẽ ra ảnh vỡ nếu dùng nguyên bản gốc ở
 * đây - đúng pattern đã áp dụng cho `CartItemRow.tsx` (task 4.3.2, xem
 * CLAUDE.md mục "Client Component KHÔNG dùng next/image").
 */
export function ProductCardClient({ product }: { product: Product }) {
  const imageUrl = resolveProductImageUrlClient(product.image_url);

  return (
    <Link
      href={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-surface transition-all duration-300 hover:-translate-y-1 hover:shadow-warm"
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-background">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-foreground-muted">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="M21 15l-5-5L5 21" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}
      </div>

      <div className="flex flex-grow flex-col p-4">
        <div className="mb-2 flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 font-heading text-base text-foreground">{product.name}</h3>
          <span
            aria-hidden="true"
            className="shrink-0 text-foreground-muted transition-colors group-hover:text-primary"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path
                d="M12 21s-7.5-4.6-10-9.1C.6 8.4 2.1 5 5.5 5c1.9 0 3.4 1 4.5 2.5C11.1 6 12.6 5 14.5 5 17.9 5 19.4 8.4 22 11.9 19.5 16.4 12 21 12 21z"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </div>

        <p className="mb-4 text-sm text-foreground-muted">{product.category.name}</p>

        <div className="mt-auto flex items-end justify-between">
          <span className="font-body text-lg font-bold text-primary">{formatPriceVnd(product.price)}</span>
          <AddToCartButton productId={product.id} disabled={product.stock_quantity <= 0} />
        </div>
      </div>
    </Link>
  );
}
