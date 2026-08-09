import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/product/Breadcrumb";
import { ProductGallery } from "@/components/product/ProductGallery";
import { ProductGrid } from "@/components/product/ProductGrid";
import { ProductInfo } from "@/components/product/ProductInfo";
import { ApiError, fetchApi } from "@/lib/api-server";
import type { Product } from "@/types/product";

type Params = Promise<{ slug: string }>;

// GET /products/{id_or_slug} (task 4.2.2) - dùng chung cho cả generateMetadata()
// lẫn component trang - Next.js tự dedupe 2 lệnh gọi fetch giống hệt nhau
// trong cùng 1 request (request memoization), không tốn thêm round-trip.
async function getProduct(slug: string): Promise<Product> {
  try {
    return await fetchApi<Product>(`/products/${slug}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const product = await fetchApi<Product>(`/products/${slug}`);
    return {
      title: `${product.name} - Vun`,
      description: product.description || `Mua ${product.name} chính hãng tại Vun.`,
    };
  } catch {
    return { title: "Sản phẩm - Vun" };
  }
}

export default async function ProductDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  const product = await getProduct(slug);

  let related: Product[] = [];
  try {
    related = await fetchApi<Product[]>(`/products/${slug}/related`);
  } catch {
    // Related chỉ là phần mở rộng - lỗi ở đây không nên chặn hiển thị chi
    // tiết sản phẩm chính, coi như không có sản phẩm liên quan.
    related = [];
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
      <Breadcrumb
        items={[
          { label: "Trang chủ", href: "/" },
          { label: "Sản phẩm", href: "/products" },
          { label: product.category.name, href: `/products?category=${product.category.id}` },
          { label: product.name },
        ]}
      />

      <section className="mb-16 grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <ProductGallery imageUrl={product.image_url} productName={product.name} />
        </div>
        <div className="lg:col-span-5 lg:pl-4">
          <ProductInfo product={product} />
        </div>
      </section>

      {related.length > 0 && (
        <section className="mb-16">
          <h2 className="mb-8 font-heading text-2xl text-foreground">Sản phẩm liên quan</h2>
          <ProductGrid products={related} />
        </section>
      )}

      <section className="mx-auto mb-16 max-w-3xl rounded-3xl bg-surface/30 py-16 text-center shadow-warm">
        <h2 className="mb-6 font-heading text-2xl text-foreground">Đánh giá sản phẩm</h2>
        <div className="flex flex-col items-center gap-4 px-6 text-foreground-secondary">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-surface text-foreground-muted">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4h16v12H8l-4 4V4Z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <p className="text-lg">Chưa có đánh giá nào.</p>
          <p className="max-w-sm text-sm opacity-80">
            Hãy là người đầu tiên chia sẻ cảm nhận về sản phẩm này với cộng đồng Vun.
          </p>
        </div>
      </section>
    </div>
  );
}
