import Link from "next/link";

/** TODO (Thành viên B): thêm menu, giỏ hàng, trạng thái đăng nhập (useAuth) khi có dữ liệu thật. */
export function Header() {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="font-heading text-lg text-primary-700">
          Vun
        </Link>
        <nav className="flex gap-6 text-sm text-foreground-secondary">
          <Link href="/products">Sản phẩm</Link>
          <Link href="/cart">Giỏ hàng</Link>
          <Link href="/orders">Đơn hàng</Link>
          <Link href="/login">Đăng nhập</Link>
        </nav>
      </div>
    </header>
  );
}
