"use client";

import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Shell 2 cột dùng chung cho /login và /register.
 * Desktop: cột form bên trái, panel thương hiệu/minh họa bên phải.
 * Mobile (<=900px, xem auth.css): form hiển thị trước để không phải cuộn trang;
 * panel minh họa thu gọn còn dải 120px bên dưới form.
 */
export function AuthLayout({
  mode,
  heading,
  subheading,
  children,
}: {
  mode: "login" | "register";
  heading: string;
  subheading: string;
  children: ReactNode;
}) {
  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-center">
          <div className="auth-brand">
            <span className="auth-brand-mark">Vun</span>
            <span className="auth-brand-tagline">Mua sắm trực tuyến</span>
          </div>

          <div className="auth-tabs">
            <Link href="/login" className={`auth-tab ${mode === "login" ? "auth-tab-active" : ""}`}>
              Đăng nhập
            </Link>
            <Link href="/register" className={`auth-tab ${mode === "register" ? "auth-tab-active" : ""}`}>
              Đăng ký
            </Link>
          </div>

          <h1 className="auth-heading">{heading}</h1>
          <p className="auth-subheading">{subheading}</p>

          {children}

          <p className="auth-switch">
            {mode === "login" ? (
              <>Chưa có tài khoản? <Link href="/register" className="auth-link auth-link-strong">Đăng ký ngay</Link></>
            ) : (
              <>Đã có tài khoản? <Link href="/login" className="auth-link auth-link-strong">Đăng nhập</Link></>
            )}
          </p>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-right-blob-1" />
        <div className="auth-right-blob-2" />
        {/* TODO: thay bằng ảnh thật (next/image) khi có asset, ví dụ public/images/auth-hero.jpg */}
        <div className="auth-image washed">
          <div className="auth-image-placeholder" />
        </div>
        <h2>Mua sắm dễ dàng, mọi lúc mọi nơi.</h2>
        <p>Vun mang đến hàng nghìn sản phẩm chất lượng từ các thương hiệu uy tín, thuộc mọi ngành hàng.</p>
        <div className="auth-tags">
          <span className="tag tag-accent-2">Giao nhanh</span>
          <span className="tag tag-accent-2">Đổi trả dễ dàng</span>
          <span className="tag tag-accent-2">Thanh toán an toàn</span>
        </div>
      </div>
    </div>
  );
}
