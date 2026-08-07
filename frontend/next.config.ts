import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // output: 'standalone' (task 2.2.2) - `next build` tự trace dependency graph
  // thật sự được import (qua Node.js module resolution), rồi copy CHỈ đúng
  // node_modules cần thiết để chạy server.js vào .next/standalone/ - không copy
  // cả node_modules đầy đủ (bao gồm devDependencies + package không dùng tới
  // lúc runtime) như build mặc định. Không ảnh hưởng `npm run dev`/`next dev` -
  // chỉ tác động `next build`, dùng bởi Dockerfile.prod.
  output: "standalone",
};

export default nextConfig;
