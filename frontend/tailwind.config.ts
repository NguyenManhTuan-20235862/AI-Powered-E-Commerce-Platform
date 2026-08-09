import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Toàn bộ giá trị bên dưới TRỎ THẲNG vào CSS custom property khai báo ở
      // app/globals.css (nguồn sự thật duy nhất, chốt từ task 1.3.4 trang
      // auth) - KHÔNG lặp lại giá trị hex/font ở đây, tránh 2 nơi phải sửa
      // khi đổi theme. Xem docs/DESIGN_TOKENS.md để biết ý nghĩa/cách dùng
      // từng token (token nào cho nền trang, token nào cho card...).
      colors: {
        background: "var(--color-bg)",
        surface: "var(--color-surface)",
        border: "color-mix(in srgb, var(--color-text) 16%, transparent)",
        foreground: {
          DEFAULT: "var(--color-text)",
          secondary: "var(--color-neutral-700)",
          muted: "var(--color-neutral-600)",
        },
        primary: {
          DEFAULT: "var(--color-accent)",
          hover: "var(--color-accent-600)",
          100: "var(--color-accent-100)",
          300: "var(--color-accent-300)",
          700: "var(--color-accent-700)",
          800: "var(--color-accent-800)",
        },
        secondary: {
          DEFAULT: "var(--color-accent-2)",
          100: "var(--color-accent-2-100)",
          300: "var(--color-accent-2-300)",
          800: "var(--color-accent-2-800)",
          900: "var(--color-accent-2-900)",
        },
        error: {
          DEFAULT: "var(--color-error)",
          container: "var(--color-error-container)",
        },
      },
      fontFamily: {
        // sans = mặc định site (body text) - trỏ luôn về Figtree, để những
        // chỗ chưa gắn class font cụ thể vẫn ra đúng font thay vì fallback
        // hệ thống. heading/body đặt tên tường minh để dùng rõ ý ở nơi cần
        // phân biệt (VD .auth-heading dùng heading, input/paragraph dùng body).
        sans: ["var(--font-body)"],
        heading: ["var(--font-heading)"],
        body: ["var(--font-body)"],
      },
      borderRadius: {
        // radius-md (16px) đã trùng khớp giá trị mặc định "2xl" của Tailwind
        // (1rem) nên KHÔNG cần khai báo thêm - dùng thẳng rounded-2xl. Chỉ
        // thêm radius-lg (28px, dùng cho auth-image/card lớn) vì Tailwind
        // mặc định không có giá trị nào khớp.
        "4xl": "28px",
      },
      boxShadow: {
        // Tương đương --shadow-lg (auth.css) - màu bóng đổ ấm (nâu tối) thay
        // vì đen thuần mặc định của Tailwind, khớp tông "warm & tin cậy".
        warm: "0 12px 32px rgba(46, 43, 37, 0.22)",
        // Task 4.2.2 - bóng đổ NHẸ hơn "warm" cho card/section tĩnh (không
        // hover), khớp đúng giá trị Stitch DESIGN.md quy định cho trang chi
        // tiết sản phẩm ("Warm Tonal Layering"): "0 8px 24px -4px rgba(32,
        // 30, 29, 0.08)" - dùng foreground (#201e1d) làm màu bóng, không
        // phải đen thuần, giữ đúng "warm & tin cậy".
        soft: "0 8px 24px -4px rgba(32, 30, 29, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
