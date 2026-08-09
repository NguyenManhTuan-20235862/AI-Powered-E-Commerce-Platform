import Link from "next/link";

const QUICK_LINKS = [
  { href: "/", label: "Trang chủ" },
  { href: "/products", label: "Sản phẩm" },
  { href: "/chat", label: "Chat AI" },
  { href: "/orders", label: "Đơn hàng của tôi" },
];

// Concept badge từ task 1.3.4 (auth-tags, trang đăng nhập/đăng ký).
const TRUST_BADGES = ["Giao nhanh", "Đổi trả dễ dàng", "Thanh toán an toàn"];

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8 sm:flex-row sm:justify-between">
        <div>
          <p className="font-heading text-lg text-primary-700">Vun</p>
          <p className="mt-1 max-w-xs text-sm text-foreground-muted">
            Mua sắm dễ dàng, mọi lúc mọi nơi — nền tảng thương mại điện tử tích hợp AI Agent.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {TRUST_BADGES.map((badge) => (
              <span key={badge} className="rounded-xl bg-secondary-100 px-3 py-1 text-xs text-secondary-800">
                {badge}
              </span>
            ))}
          </div>
        </div>

        <nav className="flex flex-col gap-2 text-sm text-foreground-secondary">
          {QUICK_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-foreground">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="border-t border-border px-4 py-4 text-center text-sm text-foreground-muted">
        © {new Date().getFullYear()} Vun - Nền tảng thương mại điện tử
      </div>
    </footer>
  );
}
