import Link from "next/link";

/** TODO (Thành viên B): thêm active state theo route, kiểm tra phân quyền role=admin. */
export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-surface">
      <div className="px-4 py-4 font-heading text-sm text-foreground">Admin</div>
      <nav className="flex flex-col gap-1 px-2 text-sm text-foreground-secondary">
        <Link href="/admin/dashboard" className="rounded px-2 py-2 hover:bg-primary-100">
          Dashboard
        </Link>
        <Link href="/admin/products" className="rounded px-2 py-2 hover:bg-primary-100">
          Quản lý sản phẩm
        </Link>
        <Link href="/admin/orders" className="rounded px-2 py-2 hover:bg-primary-100">
          Quản lý đơn hàng
        </Link>
      </nav>
    </aside>
  );
}
