import type { NextConfig } from "next";

// Cho phép next/image tải ảnh sản phẩm từ Backend (task 4.2.1, product.image_url
// là path tương đối do Backend serve qua StaticFiles - xem app/core/storage.py) -
// PHẢI dùng API_INTERNAL_URL (KHÔNG PHẢI NEXT_PUBLIC_API_URL) - route
// /_next/image LUÔN tự fetch ảnh gốc ở SERVER Next.js (bên trong container
// frontend), không phải trình duyệt - xem giải thích đầy đủ ở
// lib/format.ts:resolveProductImageUrl(). Không hardcode origin, tự đổi
// đúng theo môi trường khi biến này đổi lúc deploy (docs/ENV_VARIABLES.md).
const apiUrl = process.env.API_INTERNAL_URL ? new URL(process.env.API_INTERNAL_URL) : null;

const nextConfig: NextConfig = {
  // output: 'standalone' (task 2.2.2) - `next build` tự trace dependency graph
  // thật sự được import (qua Node.js module resolution), rồi copy CHỈ đúng
  // node_modules cần thiết để chạy server.js vào .next/standalone/ - không copy
  // cả node_modules đầy đủ (bao gồm devDependencies + package không dùng tới
  // lúc runtime) như build mặc định. Không ảnh hưởng `npm run dev`/`next dev` -
  // chỉ tác động `next build`, dùng bởi Dockerfile.prod.
  output: "standalone",
  images: apiUrl
    ? {
        remotePatterns: [
          {
            protocol: apiUrl.protocol.replace(":", "") as "http" | "https",
            hostname: apiUrl.hostname,
            port: apiUrl.port,
          },
        ],
      }
    : undefined,
};

export default nextConfig;
