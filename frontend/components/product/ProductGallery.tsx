import Image from "next/image";

import { resolveProductImageUrl } from "@/lib/format";

/**
 * Server Component - chỉ hiển thị 1 ảnh hiện tại (Backend `products.image_url`
 * chỉ 1 field, chưa hỗ trợ nhiều ảnh/gallery thật) - đặt tên tổng quát
 * "Gallery" để mở rộng sau (thumbnail switcher...) mà không phải đổi tên
 * component/props hiện có ở nơi gọi.
 */
export function ProductGallery({ imageUrl, productName }: { imageUrl: string | null; productName: string }) {
  const resolved = resolveProductImageUrl(imageUrl);

  return (
    <div className="relative flex aspect-[4/5] w-full items-center justify-center overflow-hidden rounded-3xl bg-surface p-4">
      {resolved ? (
        <div className="relative h-full w-full overflow-hidden rounded-2xl">
          <Image
            src={resolved}
            alt={productName}
            fill
            sizes="(min-width: 1024px) 58vw, 100vw"
            priority
            className="object-contain"
          />
        </div>
      ) : (
        <div className="flex h-full w-full items-center justify-center rounded-2xl bg-background text-foreground-muted">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="9" cy="9" r="2" />
            <path d="M21 15l-5-5L5 21" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      )}
    </div>
  );
}
