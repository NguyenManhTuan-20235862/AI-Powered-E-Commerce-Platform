import type { Metadata } from "next";
import { Caprasimo, Figtree } from "next/font/google";
import "./globals.css";

// Design token gốc chốt ở task 1.3.4 (trang auth, Claude Design) - task 4.1.1
// đưa việc load font này lên root layout để dùng được cho TOÀN SITE, không
// chỉ riêng route group (auth) như trước. Caprasimo chỉ có weight 400;
// Figtree dùng các weight 400/600/700. Cả hai đều là Google Fonts mã nguồn
// mở (SIL OFL), self-host lúc build qua next/font/google.
const caprasimo = Caprasimo({ weight: "400", subsets: ["latin"], variable: "--font-caprasimo" });
const figtree = Figtree({ weight: ["400", "600", "700"], subsets: ["latin"], variable: "--font-figtree" });

export const metadata: Metadata = {
  title: "AI-Powered E-Commerce Platform",
  description: "Nền tảng thương mại điện tử tích hợp AI Agent",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`${caprasimo.variable} ${figtree.variable}`}>
      <body className="min-h-screen bg-background font-body text-foreground antialiased">{children}</body>
    </html>
  );
}
