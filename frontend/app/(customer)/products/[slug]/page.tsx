import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/product/Breadcrumb";
import { ProductGallery } from "@/components/product/ProductGallery";
import { ProductGrid } from "@/components/product/ProductGrid";
import { ProductInfo } from "@/components/product/ProductInfo";
import { ProductReviews } from "@/components/product/ProductReviews";
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

      <ProductReviews productId={product.id} />
    </div>
  );
}
