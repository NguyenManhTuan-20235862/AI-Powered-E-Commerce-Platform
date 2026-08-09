import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { CartProvider } from "@/context/CartContext";
import type { Cart } from "@/types/cart";

// CheckoutForm phụ thuộc CartContext (tóm tắt đơn hàng + clearCart sau khi
// đặt thành công) VÀ useAuth() (pre-fill form) - mock cả 2 để test độc lập,
// không cần Backend thật. `mockDelete`/`mockGet`/`mockPost` dùng CHUNG 1 mock
// `@/lib/axios` (CartProvider và CheckoutForm cùng import module này).
const pushMock = vi.fn();
const replaceMock = vi.fn();
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(),
}));

// `user` PHẢI giữ NGUYÊN reference qua mọi lần render (mirror `useAuth()`
// thật - chỉ đổi reference đúng 1 lần lúc fetch xong, không đổi mỗi render) -
// CheckoutForm có `useEffect(() => { if (user) reset(...) }, [user, reset])`
// để pre-fill form; nếu mock trả về OBJECT LITERAL MỚI mỗi lần gọi (như viết
// trực tiếp trong factory `vi.mock`), `user` bị coi là "đổi" ở MỌI render ->
// effect chạy lại vô hạn -> treo test thật (đã tự gặp, dùng hết bộ nhớ node
// process tới ~840MB trước khi bị kill) - khai báo ở ngoài, dùng chung 1
// reference, tránh lặp lại lỗi này ở test khác dùng chung pattern.
const mockUser = {
  id: 1,
  email: "a@example.com",
  fullName: "Nguyễn Văn A",
  phone: "0912345678",
  address: "123 Đường ABC",
  role: "customer" as const,
};

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

const cartItem: Cart["items"][number] = {
  id: 1,
  product_id: 10,
  product_name: "Bình gốm thủ công",
  product_slug: "binh-gom-thu-cong",
  product_image_url: null,
  unit_price: "150000",
  quantity: 2,
  subtotal: "300000",
  stock_quantity: 1,
  is_active: true,
};

function renderCheckoutForm() {
  return render(
    <CartProvider>
      <CheckoutForm />
    </CartProvider>,
  );
}

describe("CheckoutForm (task 4.3.2)", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue({
      data: { success: true, message: "", data: { items: [cartItem], total_amount: "300000" } },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("pre-fill form từ user (useAuth) sau khi giỏ hàng load xong", async () => {
    renderCheckoutForm();

    await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));
    expect(screen.getByLabelText("Số điện thoại")).toHaveValue("0912345678");
    expect(screen.getByLabelText("Địa chỉ giao hàng")).toHaveValue("123 Đường ABC");
  });

  it("submit thành công - gọi POST /orders, clear giỏ hàng, redirect sang trang xác nhận kèm order_id", async () => {
    const user = userEvent.setup();
    mockPost.mockResolvedValue({
      data: {
        success: true,
        message: "Đặt hàng thành công",
        data: {
          id: 42,
          user_id: 1,
          status: "pending",
          total_amount: "300000",
          shipping_name: "Nguyễn Văn A",
          shipping_address: "123 Đường ABC",
          shipping_phone: "0912345678",
          note: null,
          items: [],
          created_at: "2026-08-09T00:00:00",
          updated_at: "2026-08-09T00:00:00",
        },
      },
    });
    mockDelete.mockResolvedValue({ data: { success: true, message: "Đã xóa toàn bộ giỏ hàng" } });

    renderCheckoutForm();
    await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));

    await user.click(screen.getByRole("button", { name: "Đặt hàng" }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith("/orders", {
        shipping_name: "Nguyễn Văn A",
        shipping_phone: "0912345678",
        shipping_address: "123 Đường ABC",
        note: undefined,
      }),
    );
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("/cart"));
    expect(pushMock).toHaveBeenCalledWith("/checkout/success?order_id=42");
  });

  it("lỗi thiếu hàng (409) - hiển thị ĐÚNG message thật từ Backend, KHÔNG redirect/clear giỏ hàng", async () => {
    const user = userEvent.setup();
    const insufficientStockError = new AxiosError(
      "Request failed with status code 409",
      "ERR_BAD_REQUEST",
      undefined,
      undefined,
      {
        status: 409,
        data: {
          success: false,
          message: 'Không thể đặt hàng: "Bình gốm thủ công" chỉ còn 1 (giỏ hàng: 2)',
        },
      } as never,
    );
    mockPost.mockRejectedValue(insufficientStockError);

    renderCheckoutForm();
    await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));

    await user.click(screen.getByRole("button", { name: "Đặt hàng" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      'Không thể đặt hàng: "Bình gốm thủ công" chỉ còn 1 (giỏ hàng: 2)',
    );
    expect(pushMock).not.toHaveBeenCalled();
    expect(mockDelete).not.toHaveBeenCalled();
  });
});
