import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { CartProvider } from "@/context/CartContext";
import type { Cart } from "@/types/cart";

// CheckoutForm phụ thuộc CartContext (tóm tắt đơn hàng + refreshCart sau khi
// đặt thành công - GET /cart để đồng bộ badge, KHÔNG DELETE) VÀ useAuth()
// (pre-fill form) - mock cả 2 để test độc lập, không cần Backend thật.
// `mockGet`/`mockPost` dùng CHUNG 1 mock `@/lib/axios` (CartProvider và
// CheckoutForm cùng import module này).
const pushMock = vi.fn();
const replaceMock = vi.fn();
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();
const mockToastError = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: vi.fn(),
  },
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

  const orderResponse = (overrides: Partial<Record<string, unknown>> = {}) => ({
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
        ...overrides,
      },
    },
  });

  it("pre-fill form từ user (useAuth) sau khi giỏ hàng load xong", async () => {
    renderCheckoutForm();

    await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));
    expect(screen.getByLabelText("Số điện thoại")).toHaveValue("0912345678");
    expect(screen.getByLabelText("Địa chỉ giao hàng")).toHaveValue("123 Đường ABC");
  });

  it("submit thành công - gọi POST /orders, đồng bộ giỏ bằng GET /cart (KHÔNG DELETE), redirect kèm order_id", async () => {
    const user = userEvent.setup();
    mockPost.mockResolvedValue(orderResponse());

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
    // Sau checkout: refreshCart() gọi GET /cart LẦN NỮA (đồng bộ badge) - GET
    // /cart phải được gọi ≥ 2 lần (mount + refresh). TUYỆT ĐỐI KHÔNG DELETE
    // /cart (Backend đã xóa trong transaction; DELETE thừa + có race xóa nhầm).
    await waitFor(() => expect(mockGet.mock.calls.filter((c) => c[0] === "/cart").length).toBeGreaterThanOrEqual(2));
    expect(mockDelete).not.toHaveBeenCalled();
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

  describe("VNPay (task \"Quyết định và hoàn thiện thanh toán\")", () => {
    let originalLocation: Location;

    beforeEach(() => {
      originalLocation = window.location;
      // @ts-expect-error - test-only: jsdom location là accessor, phải xóa trước khi gán lại.
      delete window.location;
      // @ts-expect-error - test-only stub, chỉ cần field href.
      window.location = { href: "" };
    });

    afterEach(() => {
      window.location = originalLocation;
    });

    it("chọn VNPay - đổi nhãn nút, submit gọi POST /orders RỒI POST /payments/create, điều hướng CỨNG sang payment_url", async () => {
      const user = userEvent.setup();
      mockPost.mockImplementation((url: string) => {
        if (url === "/orders") return Promise.resolve(orderResponse());
        if (url === "/payments/create") {
          return Promise.resolve({
            data: { success: true, message: "", data: { payment_id: 1, order_id: 42, payment_url: "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=1" } },
          });
        }
        throw new Error(`unexpected POST url: ${url}`);
      });

      renderCheckoutForm();
      await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));

      await user.click(screen.getByRole("radio", { name: "Thanh toán qua VNPay" }));
      expect(screen.getByRole("button", { name: "Đặt hàng & Thanh toán VNPay" })).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Đặt hàng & Thanh toán VNPay" }));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith("/payments/create", { order_id: 42 }),
      );
      expect(window.location.href).toBe("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=1");
      expect(pushMock).not.toHaveBeenCalled(); // KHÔNG router.push - điều hướng cứng thay thế
    });

    it("VNPay tạo giao dịch thất bại (VD 503 chưa cấu hình) - đơn VẪN được ghi nhận, hiện toast lỗi, fallback sang trang xác nhận COD-style", async () => {
      const user = userEvent.setup();
      mockPost.mockImplementation((url: string) => {
        if (url === "/orders") return Promise.resolve(orderResponse());
        if (url === "/payments/create") {
          return Promise.reject(
            new AxiosError("Request failed with status code 503", "ERR_BAD_REQUEST", undefined, undefined, {
              status: 503,
              data: { success: false, message: "Cổng thanh toán VNPay chưa được cấu hình" },
            } as never),
          );
        }
        throw new Error(`unexpected POST url: ${url}`);
      });

      renderCheckoutForm();
      await waitFor(() => expect(screen.getByLabelText("Họ và tên")).toHaveValue("Nguyễn Văn A"));

      await user.click(screen.getByRole("radio", { name: "Thanh toán qua VNPay" }));
      await user.click(screen.getByRole("button", { name: "Đặt hàng & Thanh toán VNPay" }));

      await waitFor(() => expect(mockToastError).toHaveBeenCalledWith("Cổng thanh toán VNPay chưa được cấu hình"));
      expect(pushMock).toHaveBeenCalledWith("/checkout/success?order_id=42");
      expect(window.location.href).toBe(""); // KHÔNG bị điều hướng cứng đi đâu
    });
  });
});
