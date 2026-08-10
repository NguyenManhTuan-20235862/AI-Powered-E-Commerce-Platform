"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/context/CartContext";

const NAV_ITEMS = [
  { href: "/", label: "Trang chủ" },
  { href: "/products", label: "Sản phẩm" },
  { href: "/chat", label: "Chat AI" },
];

export function Header() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  // task 4.3.1 - số lượng thật từ CartContext (Provider bọc ở
  // app/(customer)/layout.tsx, tự trả rỗng khi chưa đăng nhập).
  const { totalCount } = useCart();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout() {
    setIsUserMenuOpen(false);
    setIsMobileMenuOpen(false);
    await logout();
    router.push("/");
  }

  const displayName = user?.fullName || user?.email || "";

  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4">
        <Link href="/" className="font-heading text-lg text-primary-700">
          Vun
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-foreground-secondary md:flex">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-foreground">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <Link
            href="/cart"
            className="relative flex h-11 w-11 items-center justify-center text-foreground-secondary hover:text-foreground"
            aria-label="Giỏ hàng"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="9" cy="21" r="1.4" />
              <circle cx="18" cy="21" r="1.4" />
              <path d="M2.5 3h2l2.6 12.6a1.8 1.8 0 0 0 1.8 1.4h8.4a1.8 1.8 0 0 0 1.75-1.4L21.5 8H6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {totalCount > 0 && (
              <span className="absolute right-2.5 top-2.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] text-background">
                {totalCount}
              </span>
            )}
          </Link>

          <div className="hidden md:block">
            {isLoading ? (
              <div className="h-9 w-24 animate-pulse rounded-full bg-primary-100" />
            ) : isAuthenticated ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  type="button"
                  onClick={() => setIsUserMenuOpen((open) => !open)}
                  className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 hover:bg-primary-100"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary font-heading text-xs text-background">
                    {displayName.charAt(0).toUpperCase() || "?"}
                  </span>
                  <span className="max-w-[120px] truncate text-sm text-foreground">{displayName}</span>
                </button>
                {isUserMenuOpen && (
                  <div className="absolute right-0 z-10 mt-2 w-48 rounded-2xl border border-border bg-surface p-1 shadow-warm">
                    <Link
                      href="/orders"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="block rounded-xl px-3 py-2 text-sm text-foreground hover:bg-primary-100"
                    >
                      Đơn hàng của tôi
                    </Link>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="block w-full rounded-xl px-3 py-2 text-left text-sm text-foreground hover:bg-primary-100"
                    >
                      Đăng xuất
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link href="/login" className="rounded-full bg-primary px-4 py-2 font-heading text-sm text-background hover:bg-primary-hover">
                  Đăng nhập
                </Link>
                <Link href="/register" className="text-sm text-primary hover:underline">
                  Đăng ký
                </Link>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            className="flex h-11 w-11 items-center justify-center text-foreground md:hidden"
            aria-label="Mở menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>

      {isMobileMenuOpen && (
        <div className="border-t border-border px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-3 text-sm text-foreground-secondary">
            {NAV_ITEMS.map((item) => (
              <Link key={item.href} href={item.href} onClick={() => setIsMobileMenuOpen(false)} className="hover:text-foreground">
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="mt-4 border-t border-border pt-4">
            {isLoading ? (
              <div className="h-9 w-24 animate-pulse rounded-full bg-primary-100" />
            ) : isAuthenticated ? (
              <div className="flex flex-col gap-3 text-sm">
                <span className="text-foreground">{displayName}</span>
                <Link href="/orders" onClick={() => setIsMobileMenuOpen(false)} className="text-foreground-secondary hover:text-foreground">
                  Đơn hàng của tôi
                </Link>
                <button type="button" onClick={handleLogout} className="text-left text-foreground-secondary hover:text-foreground">
                  Đăng xuất
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href="/login"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="rounded-full bg-primary px-4 py-2 font-heading text-sm text-background hover:bg-primary-hover"
                >
                  Đăng nhập
                </Link>
                <Link href="/register" onClick={() => setIsMobileMenuOpen(false)} className="text-sm text-primary hover:underline">
                  Đăng ký
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
