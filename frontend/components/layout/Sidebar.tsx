"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/admin/dashboard", label: "Dashboard" },
  { href: "/admin/products", label: "Quản lý sản phẩm" },
  { href: "/admin/orders", label: "Quản lý đơn hàng" },
  { href: "/admin/users", label: "Người dùng" },
];

/** Điều hướng Admin - responsive: cột cố định trên desktop (md+), drawer trượt ra trên mobile/tablet. */
export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
        <span className="font-heading text-sm text-foreground">Admin</span>
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Mở menu quản trị"
          className="rounded p-1 text-foreground hover:bg-primary-100"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-foreground/40 md:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-56 shrink-0 transform border-r border-border bg-surface transition-transform duration-200 ease-in-out md:static md:z-auto md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <span className="font-heading text-sm text-foreground">Admin</span>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            aria-label="Đóng menu quản trị"
            className="rounded p-1 text-foreground hover:bg-primary-100 md:hidden"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <nav className="flex flex-col gap-1 px-2 text-sm text-foreground-secondary">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`rounded px-2 py-2 ${
                  isActive ? "bg-primary-100 font-medium text-primary-700" : "hover:bg-primary-100"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
