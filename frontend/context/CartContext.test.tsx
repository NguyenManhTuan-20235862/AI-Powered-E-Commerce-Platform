import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CartProvider, useCart } from "@/context/CartContext";
import type { Cart } from "@/types/cart";

// CartContext PHỤ THUỘC useAuth() (chỉ fetch giỏ hàng khi đã đăng nhập) và
// api (lib/axios.ts) cho mọi request thật - mock cả 2 để test độc lập, không
// cần Backend/token thật.
let mockIsAuthenticated = true;
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated, isLoading: false }),
}));

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

function makeCart(items: Cart["items"]): Cart {
  const total = items.reduce((sum, item) => sum + Number(item.subtotal), 0);
  return { items, total_amount: String(total) };
}

const itemA: Cart["items"][number] = {
  id: 1,
  product_id: 10,
  product_name: "Bình gốm",
  product_slug: "binh-gom",
  product_image_url: null,
  unit_price: "100000",
  quantity: 2,
  subtotal: "200000",
  stock_quantity: 5,
  is_active: true,
};

const itemB: Cart["items"][number] = {
  ...itemA,
  id: 2,
  product_id: 20,
  product_name: "Khăn vải",
  product_slug: "khan-vai",
  unit_price: "50000",
  quantity: 3,
  subtotal: "150000",
};

function CartConsumer() {
  const { items, totalCount, totalPrice, isLoading, addItem } = useCart();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="items-len">{items.length}</span>
      <span data-testid="count">{totalCount}</span>
      <span data-testid="price">{totalPrice}</span>
      <button onClick={() => addItem(10, 2)}>add</button>
    </div>
  );
}

describe("CartContext (task 4.3.1)", () => {
  afterEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
  });

  it("chưa đăng nhập - giỏ hàng rỗng, KHÔNG gọi GET /cart", async () => {
    mockIsAuthenticated = false;
    render(
      <CartProvider>
        <CartConsumer />
      </CartProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    expect(screen.getByTestId("count")).toHaveTextContent("0");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("totalCount = TỔNG quantity qua mọi dòng (không phải số dòng sản phẩm)", async () => {
    mockGet.mockResolvedValue({ data: { success: true, message: "", data: makeCart([itemA, itemB]) } });

    render(
      <CartProvider>
        <CartConsumer />
      </CartProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));
    // 2 dòng sản phẩm khác nhau (itemA quantity=2, itemB quantity=3) ->
    // totalCount phải = 5 (tổng cộng dồn), KHÔNG PHẢI 2 (items.length).
    expect(screen.getByTestId("items-len")).toHaveTextContent("2");
    expect(screen.getByTestId("count")).toHaveTextContent("5");
    expect(screen.getByTestId("price")).toHaveTextContent("350000");
  });

  it("addItem cộng dồn đúng - state lấy TRỰC TIẾP từ response Backend, không tự cộng ở client", async () => {
    const user = userEvent.setup();
    mockGet.mockResolvedValue({ data: { success: true, message: "", data: makeCart([]) } });
    // Backend đã cộng dồn sẵn (sản phẩm 10 đã có quantity=2 trong giỏ, thêm 2
    // nữa -> trả về quantity=4) - Context PHẢI hiển thị đúng số Backend trả
    // về, không phải 2 (giá trị vừa gửi lên) hay tự cộng thủ công ở client.
    const accumulatedItem = { ...itemA, quantity: 4, subtotal: "400000" };
    mockPost.mockResolvedValue({
      data: { success: true, message: "Đã thêm vào giỏ hàng", data: makeCart([accumulatedItem]) },
    });

    render(
      <CartProvider>
        <CartConsumer />
      </CartProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("loading")).toHaveTextContent("false"));

    await user.click(screen.getByText("add"));

    expect(mockPost).toHaveBeenCalledWith("/cart/items", { product_id: 10, quantity: 2 });
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("4"));
    expect(screen.getByTestId("items-len")).toHaveTextContent("1");
  });
});
