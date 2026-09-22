import Link from "next/link";

import { ProductGrid } from "@/components/product/ProductGrid";
import { fetchApi } from "@/lib/api-server";
import type { Category } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";
import type { Product } from "@/types/product";

// Số sản phẩm hiện ở "Sản phẩm nổi bật" - khớp lưới 3 cột `ProductGrid`
// (2-3 hàng đẹp mắt), không cần page_size lớn cho khu vực giới thiệu.
const FEATURED_PRODUCTS_LIMIT = 8;

// 6 danh mục hiện ở trang chủ (theo đúng yêu cầu xác nhận trước khi port) -
// `GET /categories` thật trả 9 danh mục (gồm cả 3 danh mục "thủ công" seed
// từ task 4.2.1: Gốm sứ/Đồ gỗ/Vải dệt) - lọc theo `slug` (ổn định hơn so
// khớp theo `name` hiển thị) để CHỈ hiện đúng 6 danh mục demo đã xác nhận.
// Tên/id/mô tả hiển thị vẫn lấy THẬT từ API, KHÔNG hard-code text - đây chỉ
// là danh sách slug dùng để CHỌN đúng 6 danh mục, không phải nội dung hiển thị.
const FEATURED_CATEGORY_SLUGS = ["dien-tu", "thoi-trang", "nha-cua", "lam-dep", "do-choi", "sach"];

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  "dien-tu": (
    <>
      <rect x="4" y="4" width="16" height="11" rx="1.5" />
      <path d="M9 20h6M12 15v5" strokeLinecap="round" />
    </>
  ),
  "thoi-trang": (
    <path
      d="M8 4 5 6l1.5 3H8v11h8V9h1.5L19 6l-3-2-2 2h-4l-2-2Z"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  "nha-cua": (
    <path d="M4 11 12 4l8 7M6 10v9h12v-9" strokeLinecap="round" strokeLinejoin="round" />
  ),
  "lam-dep": (
    <path
      d="M12 3c1 2.5 2.5 4 5 5-2.5 1-4 2.5-5 5-1-2.5-2.5-4-5-5 2.5-1 4-2.5 5-5ZM18 15c.5 1.2 1.3 2 2.5 2.5-1.2.5-2 1.3-2.5 2.5-.5-1.2-1.3-2-2.5-2.5 1.2-.5 2-1.3 2.5-2.5Z"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  "do-choi": (
    <path
      d="M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  sach: (
    <path
      d="M4 5.5C4 4.7 4.7 4 5.5 4H12v16H5.5c-.8 0-1.5-.7-1.5-1.5v-13ZM20 5.5c0-.8-.7-1.5-1.5-1.5H12v16h6.5c.8 0 1.5-.7 1.5-1.5v-13Z"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
};

const TRUST_BADGES = [
  {
    title: "Giao nhanh toàn quốc",
    description: "Đóng gói cẩn trọng, vận chuyển tận tay",
    icon: (
      <path
        d="M3 7h11v8H3zM14 10h4l3 3v2h-7v-5ZM6 18a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM17 18a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Đổi trả dễ dàng",
    description: "Yên tâm tuyệt đối khi nhận hàng",
    icon: (
      <path
        d="M3 12a9 9 0 1 1 3 6.7M3 12v5h5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Thanh toán an toàn",
    description: "Đa dạng phương thức tiện lợi, an toàn",
    icon: (
      <path
        d="M12 3l8 3.5v5c0 5-3.4 8.4-8 9.5-4.6-1.1-8-4.5-8-9.5v-5L12 3Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
];

async function getHomeData() {
  const productsQuery = new URLSearchParams({ page: "1", page_size: String(FEATURED_PRODUCTS_LIMIT) });
  const [categories, products] = await Promise.all([
    fetchApi<Category[]>("/categories"),
    fetchApi<PaginatedResponse<Product>>("/products", productsQuery),
  ]);

  const featuredCategories = FEATURED_CATEGORY_SLUGS.map((slug) =>
    categories.find((category) => category.slug === slug),
  ).filter((category): category is Category => category !== undefined);

  return { featuredCategories, featuredProducts: products.items };
}

export default async function HomePage() {
  const { featuredCategories, featuredProducts } = await getHomeData();

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-12 px-4 py-8">
      {/* 1. HERO */}
      <section className="relative overflow-hidden rounded-4xl bg-surface px-6 py-16 text-center shadow-soft sm:px-12 sm:py-20">
        <div className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full bg-primary-100 opacity-60 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 left-1/4 h-64 w-64 rounded-full bg-secondary-100 opacity-60 blur-3xl" />
        <div className="relative flex flex-col items-center gap-5">
          <h1 className="max-w-2xl font-heading text-3xl text-foreground sm:text-5xl">
            Mua sắm dễ dàng, mọi lúc mọi nơi
          </h1>
          <p className="max-w-xl text-foreground-secondary">
            Vun — nền tảng thương mại điện tử tích hợp AI Agent, giúp bạn tìm đúng sản phẩm mình cần nhanh chóng.
          </p>
          <Link
            href="/products"
            className="mt-2 rounded-full bg-primary px-8 py-3 font-heading text-sm text-background transition-colors hover:bg-primary-hover"
          >
            Khám phá ngay
          </Link>
        </div>
      </section>

      {/* 2. TRUST BADGES */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {TRUST_BADGES.map((badge) => (
          <div key={badge.title} className="flex items-center gap-4 rounded-2xl bg-surface p-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-secondary-100 text-secondary-800">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                {badge.icon}
              </svg>
            </div>
            <div>
              <p className="font-heading text-sm text-foreground">{badge.title}</p>
              <p className="text-sm text-foreground-muted">{badge.description}</p>
            </div>
          </div>
        ))}
      </section>

      {/* 3. DANH MỤC NGÀNH HÀNG */}
      {featuredCategories.length > 0 && (
        <section className="flex flex-col gap-5">
          <div className="flex items-end justify-between gap-3">
            <h2 className="font-heading text-2xl text-foreground">Khám phá theo danh mục</h2>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {featuredCategories.map((category) => (
              <Link
                key={category.id}
                href={`/products?category=${category.id}`}
                className="group flex flex-col items-center gap-2 rounded-2xl bg-surface p-4 text-center transition-all hover:-translate-y-1 hover:shadow-warm"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-primary transition-colors group-hover:bg-primary group-hover:text-background">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    {CATEGORY_ICONS[category.slug]}
                  </svg>
                </div>
                <span className="font-heading text-sm text-foreground">{category.name}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 4. SẢN PHẨM NỔI BẬT */}
      <section className="flex flex-col gap-5">
        <div className="flex items-end justify-between gap-3">
          <h2 className="font-heading text-2xl text-foreground">Sản phẩm nổi bật</h2>
          <Link href="/products" className="text-sm font-medium text-primary hover:text-primary-hover">
            Xem tất cả →
          </Link>
        </div>
        <ProductGrid products={featuredProducts} />
      </section>
    </div>
  );
}
