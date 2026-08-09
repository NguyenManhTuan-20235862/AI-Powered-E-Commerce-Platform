"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { extractApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/axios";
import { useAuth } from "@/hooks/useAuth";
import type { ApiResponse } from "@/types/common";
import type { Cart } from "@/types/cart";

const EMPTY_CART: Cart = { items: [], total_amount: "0" };

interface CartContextValue {
  items: Cart["items"];
  // Tổng SỐ LƯỢNG cộng dồn qua mọi dòng (VD 2 sản phẩm khác nhau, mỗi cái
  // quantity 3 -> totalCount = 6) - đúng quy ước badge giỏ hàng phổ biến
  // (Shopee/Tiki/Amazon), KHÔNG PHẢI số dòng sản phẩm khác nhau (items.length).
  totalCount: number;
  // string (không phải number) - cùng lý do Cart.total_amount: giữ nguyên giá
  // trị Decimal Backend trả về, hiển thị qua formatPriceVnd() ở nơi dùng.
  totalPrice: string;
  isLoading: boolean;
  isAuthenticated: boolean;
  addItem: (productId: number, quantity?: number) => Promise<void>;
  updateQuantity: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  clearCart: () => Promise<void>;
}

const CartContext = createContext<CartContextValue | null>(null);

/**
 * CartProvider (task 4.3.1) - state giỏ hàng dùng CHUNG cho Header (badge) +
 * ProductCard (catalog) + ProductInfo (chi tiết), đặt ở `app/(customer)/layout.tsx`
 * (chỉ route Customer cần giỏ hàng, Admin không có ý nghĩa - đúng như Backend
 * `require_role(UserRole.customer)` chặn Admin ở mọi endpoint /cart).
 *
 * Nguồn sự thật LUÔN là response `CartRead` Backend trả về sau mỗi action -
 * KHÔNG tự cộng/trừ số lượng ở client (tránh lệch nếu Backend từ chối 1 phần,
 * VD cộng dồn vượt tồn kho) - mọi action set lại state trực tiếp từ response.
 *
 * Chỉ fetch giỏ hàng khi ĐÃ đăng nhập (`useAuth()`) - gọi GET /cart lúc chưa
 * có token sẽ luôn 401, không có ý nghĩa. `isAuthenticated` cũng export ra
 * ngoài để các component thêm-vào-giỏ (AddToCartButton/AddToCartSection) dùng
 * chung, tránh mỗi nơi tự gọi `useAuth()` riêng (mỗi lần gọi lại tốn 1 request
 * GET /auth/me - xem hooks/useAuth.ts).
 */
export function CartProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [cart, setCart] = useState<Cart>(EMPTY_CART);
  const [isCartLoading, setIsCartLoading] = useState(true);

  const fetchCart = useCallback(async () => {
    try {
      const { data } = await api.get<ApiResponse<Cart>>("/cart");
      setCart(data.data);
    } catch {
      setCart(EMPTY_CART);
    }
  }, []);

  useEffect(() => {
    if (isAuthLoading) return;
    if (!isAuthenticated) {
      setCart(EMPTY_CART);
      setIsCartLoading(false);
      return;
    }
    setIsCartLoading(true);
    fetchCart().finally(() => setIsCartLoading(false));
  }, [isAuthenticated, isAuthLoading, fetchCart]);

  const addItem = useCallback(async (productId: number, quantity = 1) => {
    const { data } = await api.post<ApiResponse<Cart>>("/cart/items", { product_id: productId, quantity });
    setCart(data.data);
  }, []);

  const updateQuantity = useCallback(async (itemId: number, quantity: number) => {
    const { data } = await api.put<ApiResponse<Cart>>(`/cart/items/${itemId}`, { quantity });
    setCart(data.data);
  }, []);

  const removeItem = useCallback(async (itemId: number) => {
    const { data } = await api.delete<ApiResponse<Cart>>(`/cart/items/${itemId}`);
    setCart(data.data);
  }, []);

  const clearCart = useCallback(async () => {
    await api.delete("/cart");
    setCart(EMPTY_CART);
  }, []);

  const totalCount = useMemo(() => cart.items.reduce((sum, item) => sum + item.quantity, 0), [cart.items]);

  const value: CartContextValue = {
    items: cart.items,
    totalCount,
    totalPrice: cart.total_amount,
    isLoading: isAuthLoading || isCartLoading,
    isAuthenticated,
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart() phải dùng bên trong <CartProvider>");
  return ctx;
}

/** Helper dùng chung cho component thêm-vào-giỏ: rút message lỗi thật từ Backend. */
export function cartErrorMessage(err: unknown): string {
  return extractApiErrorMessage(err, "Không thể thêm vào giỏ hàng. Vui lòng thử lại.");
}
