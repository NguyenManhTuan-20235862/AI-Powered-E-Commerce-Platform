"use client";

/**
 * Error boundary CHO CHÍNH ROOT LAYOUT (`app/layout.tsx`) - KHÁC `error.tsx`
 * (chỉ bắt lỗi trong `children`, layout gốc vẫn còn sống). Next.js quy định
 * tên file cố định này CHỈ kích hoạt khi bản thân `RootLayout` throw (hiếm -
 * VD lỗi trong chính `AuthProvider`/`Toaster` ở layout.tsx) - lúc đó layout
 * gốc COI NHƯ KHÔNG CÒN, `global-error.tsx` PHẢI tự khai LẠI `<html>`/`<body>`
 * (Next.js docs) vì nó THAY THẾ hoàn toàn layout gốc, không lồng bên trong.
 *
 * CỐ TÌNH giữ thật đơn giản - không import font/Provider nào (những thứ vừa
 * gây lỗi tầng layout gốc có thể chính là 1 trong các import đó) - chỉ CSS
 * inline tối thiểu, không phụ thuộc Tailwind class/design token (rủi ro
 * `globals.css` cũng không áp dụng được nếu lỗi xảy ra sớm trong quá trình
 * render layout).
 */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="vi">
      <body
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "16px",
          fontFamily: "sans-serif",
          textAlign: "center",
          padding: "24px",
        }}
      >
        <h1 style={{ fontSize: "24px", margin: 0 }}>Đã có lỗi nghiêm trọng xảy ra</h1>
        <p style={{ color: "#645c50", margin: 0 }}>Rất tiếc, ứng dụng gặp sự cố ngoài dự kiến. Vui lòng thử lại.</p>
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            type="button"
            onClick={reset}
            style={{
              borderRadius: "999px",
              padding: "12px 24px",
              background: "#c67139",
              color: "#fff",
              border: "none",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Thử lại
          </button>
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- `<a>` thuần CÓ CHỦ Ý
              (không phải next/link): global-error.tsx thay thế hẳn RootLayout lúc kích hoạt,
              không nên phụ thuộc router context có thể đã hỏng cùng lúc layout gốc throw. */}
          <a
            href="/"
            style={{
              borderRadius: "999px",
              padding: "12px 24px",
              border: "1px solid #82796a",
              color: "#201e1d",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            Về trang chủ
          </a>
        </div>
      </body>
    </html>
  );
}
