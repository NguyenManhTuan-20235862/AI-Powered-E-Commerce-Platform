import type { ReactNode } from "react";
import "./auth.css";

// Chỉ áp dụng cho route group (auth) - layout full-bleed 2 cột riêng, không dùng
// khung Tailwind căn giữa mặc định của app. Font Caprasimo/Figtree được load
// ở root layout.tsx (task 4.1.1, dùng chung toàn site) - route group này chỉ
// cần import auth.css (class riêng cho layout 2 cột), không tự load font nữa.
export default function AuthRouteLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
