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
      colors: {
        // Màu trung tính tạm thời cho thương hiệu TMĐT - tinh chỉnh sau.
        brand: {
          50: "#f5f7fa",
          100: "#e9edf3",
          200: "#cdd6e3",
          300: "#a3b2c9",
          400: "#7188aa",
          500: "#4d6690",
          600: "#3a5075",
          700: "#2f405f",
          800: "#293650",
          900: "#252e44",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
