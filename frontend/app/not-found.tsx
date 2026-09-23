import Link from "next/link";

/**
 * Trang 404 CHUNG cho toàn site (task "Dọn frontend để không còn màn hình
 * giả") - trước đây KHÔNG có file này, Next.js tự render trang 404 mặc định
 * (trắng, không theo design token, không có cách quay lại) cho MỌI URL không
 * khớp route nào. Next.js tự dùng file này (App Router quy ước tên cố định)
 * cho CẢ 2 trường hợp: điều hướng thật tới URL không tồn tại, VÀ khi code
 * gọi `notFound()` (VD `app/(customer)/products/[slug]/page.tsx` khi
 * `GET /products/{id_or_slug}` trả 404).
 *
 * Render như 1 page.tsx thường (KHÔNG cần tự khai `<html>`/`<body>` - vẫn
 * nằm TRONG `RootLayout`, khác `global-error.tsx`).
 */
export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-4 px-4 py-16 text-center">
      <p className="font-heading text-6xl text-primary">404</p>
      <h1 className="font-heading text-2xl text-foreground">Không tìm thấy trang này</h1>
      <p className="text-foreground-secondary">
        Trang bạn đang tìm có thể đã bị xóa, đổi địa chỉ, hoặc chưa từng tồn tại.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
      >
        Về trang chủ
      </Link>
    </div>
  );
}
