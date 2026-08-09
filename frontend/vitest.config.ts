import { fileURLToPath } from "url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Vitest lần đầu tiên trong dự án (task 4.2.3) - test component Client
// ("use client") độc lập, không cần dev server/browser thật, KHÁC hẳn cách
// verify Frontend đã dùng xuyên suốt trước giờ (browser automation thủ công
// mỗi task). Dùng cho case cần assert HÀNH VI RE-RENDER cụ thể (VD bug đồng
// bộ state theo searchParams đổi từ bên ngoài, task 4.2.3) - khó/chậm hơn
// nhiều nếu chỉ verify bằng browser thật.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Khớp "paths": { "@/*": ["./*"] } trong tsconfig.json - Vitest (Vite)
      // không tự đọc tsconfig paths, phải khai lại thủ công ở đây.
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
});
