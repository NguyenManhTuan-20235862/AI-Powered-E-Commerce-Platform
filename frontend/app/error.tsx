"use client";

import Link from "next/link";

/**
 * Error boundary CHUNG cho toàn site (task "Dọn frontend để không còn màn
 * hình giả") - trước đây KHÔNG có file này, 1 lỗi render bất ngờ (throw
 * ngoài dự kiến trong bất kỳ Server/Client Component nào dưới layout gốc)
 * làm Next.js tự hiện màn hình lỗi mặc định (trắng, kỹ thuật, không thân
 * thiện). File này CHỈ bắt lỗi RENDER (throw trong component) - KHÔNG bắt
 * lỗi API (`try/catch` quanh `api.get/post` ở từng component vẫn là nơi xử
 * lý đúng cho lỗi mạng/4xx/5xx, xem `extractApiErrorMessage()` - 2 tầng khác
 * nhau, không thay thế nhau).
 *
 * BẮT BUỘC `"use client"` (Next.js quy định - error boundary luôn Client
 * Component, dùng React error boundary phía dưới). Vẫn nằm TRONG
 * `RootLayout` (KHÔNG cần tự khai `<html>`/`<body>` - khác `global-error.tsx`,
 * chỉ dùng khi chính ROOT LAYOUT throw).
 */
export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-4 px-4 py-16 text-center">
      <h1 className="font-heading text-2xl text-foreground">Đã có lỗi xảy ra</h1>
      <p className="text-foreground-secondary">Rất tiếc, trang gặp sự cố ngoài dự kiến. Vui lòng thử lại.</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-full bg-primary px-6 py-3 font-heading text-sm text-background hover:bg-primary-hover"
        >
          Thử lại
        </button>
        <Link
          href="/"
          className="rounded-full border border-border px-6 py-3 font-heading text-sm text-foreground hover:bg-primary-100"
        >
          Về trang chủ
        </Link>
      </div>
    </div>
  );
}
