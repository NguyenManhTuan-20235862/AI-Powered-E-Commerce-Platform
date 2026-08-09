import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { CartProvider } from "@/context/CartContext";

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  return (
    <CartProvider>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    </CartProvider>
  );
}
