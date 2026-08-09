import { AddToCartSection } from "@/components/product/AddToCartSection";
import { formatPriceVnd } from "@/lib/format";
import type { Product } from "@/types/product";

const TRUST_BADGES = [
  {
    label: "Giao nhanh",
    icon: (
      <path d="M3 16V6a1 1 0 0 1 1-1h9v11H4a1 1 0 0 1-1-1Zm10-9h4l3 4v5h-2M13 16h4M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
    ),
  },
  {
    label: "Đổi trả dễ dàng",
    icon: <path d="M4 4v5h5M20 20v-5h-5M4.5 9a8 8 0 0 1 14.5-3M19.5 15a8 8 0 0 1-14.5 3" strokeLinecap="round" strokeLinejoin="round" />,
  },
  {
    label: "Thanh toán an toàn",
    icon: <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Zm-2.5 9 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />,
  },
];

// products.description (Backend) là 1 cột TEXT, có thể chứa nhiều đoạn phân
// tách bằng dòng trống - tách ra hiển thị từng <p> cho dễ đọc thay vì 1 khối
// văn bản dài, không đổi/thêm gì vào dữ liệu gốc.
function descriptionParagraphs(description: string): string[] {
  return description
    .split(/\n+/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

export function ProductInfo({ product }: { product: Product }) {
  const inStock = product.stock_quantity > 0;

  return (
    <div className="flex flex-col">
      <span className="mb-4 w-fit rounded-full bg-secondary-100 px-4 py-1.5 text-xs font-semibold text-secondary-800">
        {product.category.name}
      </span>

      <h1 className="mb-4 font-heading text-3xl text-foreground md:text-4xl">{product.name}</h1>

      <div className="mb-6 flex items-center gap-6 border-b border-border pb-6">
        <span className="font-body text-2xl font-semibold text-primary">{formatPriceVnd(product.price)}</span>
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${inStock ? "bg-secondary" : "bg-foreground-muted"}`} />
          <span className={`text-sm font-semibold ${inStock ? "text-secondary" : "text-foreground-muted"}`}>
            {inStock ? "Còn hàng" : "Hết hàng"}
          </span>
        </div>
      </div>

      {product.description && (
        <div className="mb-8 space-y-4 leading-relaxed text-foreground-secondary">
          {descriptionParagraphs(product.description).map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </div>
      )}

      <AddToCartSection productId={product.id} stockQuantity={product.stock_quantity} />

      <div className="grid grid-cols-3 gap-4 border-t border-border pt-6">
        {TRUST_BADGES.map((badge) => (
          <div key={badge.label} className="flex flex-col items-center gap-2 text-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="text-secondary" aria-hidden="true">
              {badge.icon}
            </svg>
            <span className="text-xs text-foreground-secondary">{badge.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
