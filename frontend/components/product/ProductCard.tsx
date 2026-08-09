import Image from "next/image";
import Link from "next/link";

import { formatPriceVnd, resolveProductImageUrl } from "@/lib/format";
import type { Product } from "@/types/product";

/**
 * Server Component - không cần "use client": chỉ hiển thị, không có state/
 * event handler thật. Nút giỏ hàng/yêu thích để DECORATIVE (không onClick) -
 * thêm giỏ hàng thật thuộc task 4.3 (GET/POST /cart), chưa tích hợp ở đây,
 * tương tự cách Header (task 4.1.2) để badge giỏ hàng tĩnh chờ task 4.3.
 */
export function ProductCard({ product }: { product: Product }) {
  const imageUrl = resolveProductImageUrl(product.image_url);

  return (
    <Link
      href={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-surface transition-all duration-300 hover:-translate-y-1 hover:shadow-warm"
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-background">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={product.name}
            fill
            sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
            className="object-cover transition-transform duration-700 group-hover:scale-105"
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
          <span
            aria-hidden="true"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-background text-foreground-muted transition-colors group-hover:bg-primary group-hover:text-background"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="9" cy="21" r="1.4" />
              <circle cx="18" cy="21" r="1.4" />
              <path d="M2.5 3h2l2.6 12.6a1.8 1.8 0 0 0 1.8 1.4h8.4a1.8 1.8 0 0 0 1.75-1.4L21.5 8H6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}
