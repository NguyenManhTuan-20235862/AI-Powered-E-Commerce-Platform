import type { ReactNode } from "react";
import { Caprasimo, Figtree } from "next/font/google";
import "./auth.css";

// Caprasimo chỉ có weight 400; Figtree dùng các weight 400/600/700.
// Cả hai đều là Google Fonts mã nguồn mở (SIL OFL), self-host lúc build qua next/font/google.
const caprasimo = Caprasimo({ weight: "400", subsets: ["latin"], variable: "--font-caprasimo" });
const figtree = Figtree({ weight: ["400", "600", "700"], subsets: ["latin"], variable: "--font-figtree" });

// Chỉ áp dụng cho route group (auth) - layout full-bleed 2 cột riêng, không dùng
// khung Tailwind căn giữa mặc định của app.
export default function AuthRouteLayout({ children }: { children: ReactNode }) {
  return <div className={`${caprasimo.variable} ${figtree.variable}`}>{children}</div>;
}
