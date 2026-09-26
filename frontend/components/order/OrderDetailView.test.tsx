import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OrderDetailView } from "@/components/order/OrderDetailView";
import type { OrderStatusEvent } from "@/types/notification";
import type { Order } from "@/types/order";

const mockGet = vi.fn();
const mockPut = vi.fn();
const mockPost = vi.fn();
const replaceMock = vi.fn();
const mockToastError = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    put: (...args: unknown[]) => mockPut(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: vi.fn(),
  },
}));

// Object router khai 1 LẦN ở module scope (KHÔNG tạo mới bên trong factory)
// - giữ identity ỔN ĐỊNH qua mọi lần render, đúng hành vi Next.js thật (xem
// giải thích đầy đủ ở OrdersView.test.tsx, nơi lỗi này từng gây test flaky
// thật do fetchOrders phụ thuộc `router`).
const routerMock = { replace: replaceMock, push: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
}));

// useOrderStatusStream (task 5.2.2) đã có test riêng đầy đủ ở
// hooks/useOrderStatusStream.test.ts (vòng đời EventSource/backoff/token hết
// hạn) - ở đây CHỈ cần xác nhận OrderDetailView TRUYỀN ĐÚNG onOrderStatus và
// PHẢN ỨNG đúng khi hook gọi callback đó (lọc đúng order_id, refetch) - mock
// thẳng hook, không cần dựng lại FakeEventSource.
let capturedOnOrderStatus: ((event: OrderStatusEvent) => void) | null = null;
const retryStreamMock = vi.fn();
vi.mock("@/hooks/useOrderStatusStream", () => ({
  useOrderStatusStream: (opts: { onOrderStatus: (event: OrderStatusEvent) => void }) => {
    capturedOnOrderStatus = opts.onOrderStatus;
    return { status: "open", retryNow: retryStreamMock };
  },
}));

const baseOrder: Order = {
  id: 10,
  user_id: 1,
  status: "pending",
  total_amount: "300000",
  shipping_name: "Nguyễn Văn A",
  shipping_address: "123 Đường ABC",
  shipping_phone: "0912345678",
  note: "Giao giờ hành chính",
  items: [{ id: 1, product_id: 1, product_name: "Bình gốm", quantity: 2, price_at_purchase: "150000" }],
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

function okResponse(order: Order) {
  return { data: { success: true, message: "", data: order } };
}

function httpError(statusCode: number, message = "") {
  return new AxiosError(
    `Request failed with status code ${statusCode}`,
    "ERR_BAD_REQUEST",
    undefined,
    undefined,
    { status: statusCode, data: { success: false, message } } as never,
  );
}

function networkError() {
  return new AxiosError("Network Error", "ERR_NETWORK");
}

type MockOutcome = { ok: true; data: unknown } | { ok: false; error: unknown };

/**
 * `mockGet` giờ dùng chung cho CẢ `GET /orders/{id}` LẪN `GET
 * /payments/{id}/status` (task "Quyết định và hoàn thiện thanh toán" - thêm
 * khối "Thanh toán") - dispatch theo URL thay vì trả `mockResolvedValue`
 * chung chung cho MỌI lời gọi (sẽ khiến lời gọi payment "vô tình" nhận nhầm
 * dữ liệu đơn hàng). Mặc định `/payments/{id}/status` trả 404 (đơn COD,
 * KHÔNG có giao dịch VNPay nào - đúng hành vi thật đa số test ở đây đang mô
 * phỏng) trừ khi 1 test cụ thể gọi `mockPaymentResponse()` để đổi.
 *
 * `orderOutcomes` (mảng) - PHÁT theo ĐÚNG THỨ TỰ cho MỖI lời gọi `/orders/{id}`
 * kế tiếp (phần tử CUỐI lặp lại vô hạn nếu gọi nhiều hơn số phần tử đã khai)
 * - tách biệt hẳn khỏi số lần gọi `/payments/.../status` (không còn lẫn lộn
 * như đếm chung `mockGet.mock.calls.length` trước đây).
 */
function mockOrderOutcomes(orderId: number, ...orderOutcomes: MockOutcome[]) {
  let call = 0;
  mockGet.mockImplementation((url: string) => {
    if (url === `/payments/${orderId}/status`) {
      return Promise.reject(httpError(404, "Đơn hàng này chưa có giao dịch thanh toán online"));
    }
    const outcome = orderOutcomes[Math.min(call, orderOutcomes.length - 1)];
    call += 1;
    return outcome.ok ? Promise.resolve(outcome.data) : Promise.reject(outcome.error);
  });
}

/** Cùng `mockOrderOutcomes()` nhưng `/payments/{orderId}/status` trả về
 * `paymentData` THẬT (thay vì mặc định 404 "chưa có giao dịch") - dùng cho
 * test khối "Thanh toán". */
function mockOrderOutcomesWithPayment(orderId: number, paymentData: unknown, ...orderOutcomes: MockOutcome[]) {
  let call = 0;
  mockGet.mockImplementation((url: string) => {
    if (url === `/payments/${orderId}/status`) {
      return Promise.resolve(paymentData);
    }
    const outcome = orderOutcomes[Math.min(call, orderOutcomes.length - 1)];
    call += 1;
    return outcome.ok ? Promise.resolve(outcome.data) : Promise.reject(outcome.error);
  });
}

function countCallsTo(url: string): number {
  return mockGet.mock.calls.filter((call) => call[0] === url).length;
}

function paymentResponse(status: "pending" | "success" | "failed" | "refunded", orderId = 10) {
  return {
    data: {
      success: true,
      message: "",
      data: {
        order_id: orderId,
        payment_method: "vnpay",
        transaction_id: status === "success" ? "14000123" : null,
        amount: "300000",
        status,
        created_at: "2026-08-01T00:00:00",
        updated_at: "2026-08-01T00:00:00",
      },
    },
  };
}

describe("OrderDetailView (hoàn thiện /orders/[id])", () => {
  beforeEach(() => {
    vi.spyOn(window, "confirm");
    capturedOnOrderStatus = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPut.mockReset();
    mockPost.mockReset();
    mockToastError.mockReset();
    replaceMock.mockReset();
    retryStreamMock.mockReset();
  });

  it("hiện 'Đang tải...' trước khi fetch xong", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // chưa bao giờ resolve
    render(<OrderDetailView orderId={10} />);
    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
  });

  it("fetch thành công - hiện đủ trạng thái, snapshot sản phẩm, tổng tiền, người nhận, ghi chú, thời gian", async () => {
    mockOrderOutcomes(10, { ok: true, data: okResponse(baseOrder) });
    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Đơn hàng #10")).toBeInTheDocument();
    expect(screen.getByText("Chờ xác nhận")).toBeInTheDocument(); // OrderStatusBadge
    expect(screen.getByText("Bình gốm")).toBeInTheDocument();
    expect(screen.getByText(/150.000 ₫.*2/)).toBeInTheDocument();
    // "300.000 ₫" xuất hiện Ở CẢ subtotal dòng sản phẩm (150.000 x 2) LẪN
    // tổng tiền đơn - scope theo dòng "Tổng cộng" để không mơ hồ giữa 2 chỗ.
    expect(screen.getByText("Tổng cộng").closest("div")).toHaveTextContent("300.000 ₫");
    expect(screen.getByText("Nguyễn Văn A")).toBeInTheDocument();
    expect(screen.getByText("0912345678")).toBeInTheDocument();
    expect(screen.getByText("123 Đường ABC")).toBeInTheDocument();
    expect(screen.getByText("Giao giờ hành chính")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith("/orders/10");
  });

  // KHÔNG còn test "401 -> điều hướng /login" ở đây - trách nhiệm này đã
  // chuyển hẳn về `lib/axios.ts` (interceptor tự điều hướng + "bỏ rơi"
  // promise, xem `axios.test.ts`) sau khi dọn dẹp 2 cơ chế redirect race
  // nhau (task "Dọn frontend để không còn màn hình giả") - component này
  // giờ KHÔNG BAO GIỜ nhận được 1 lỗi 401 thật để mà catch (promise từ
  // `api.get()` không bao giờ resolve/reject cho case đó trong thực tế),
  // nên mock `mockGet.mockRejectedValue(httpError(401))` không còn phản ánh
  // đúng hành vi thật nữa.

  it("403 - hiện thông báo không có quyền + link quay lại, KHÔNG điều hướng /login", async () => {
    mockOrderOutcomes(10, { ok: false, error: httpError(403) });
    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Bạn không có quyền xem đơn hàng này.")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("404 - hiện thông báo không tìm thấy đơn hàng", async () => {
    mockOrderOutcomes(999, { ok: false, error: httpError(404) });
    render(<OrderDetailView orderId={999} />);

    expect(await screen.findByText("Không tìm thấy đơn hàng này.")).toBeInTheDocument();
  });

  it("lỗi mạng - hiện thông báo + nút Thử lại, bấm Thử lại gọi lại API", async () => {
    const user = userEvent.setup();
    mockOrderOutcomes(10, { ok: false, error: networkError() }, { ok: true, data: okResponse(baseOrder) });

    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và thử lại.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(await screen.findByText("Đơn hàng #10")).toBeInTheDocument();
    expect(countCallsTo("/orders/10")).toBe(2);
  });

  it("lỗi 500 - hiện message thật từ Backend + nút Thử lại", async () => {
    mockOrderOutcomes(10, { ok: false, error: httpError(500, "Lỗi hệ thống, vui lòng thử lại sau") });
    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Lỗi hệ thống, vui lòng thử lại sau")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeInTheDocument();
  });

  it("status=pending - hiện nút Hủy đơn hàng; xác nhận confirm() -> PUT /orders/{id}/cancel, cập nhật lại trạng thái hiển thị", async () => {
    const user = userEvent.setup();
    vi.mocked(window.confirm).mockReturnValue(true);
    mockOrderOutcomes(10, { ok: true, data: okResponse(baseOrder) });
    mockPut.mockResolvedValue(okResponse({ ...baseOrder, status: "cancelled" }));

    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    await user.click(screen.getByRole("button", { name: "Hủy đơn hàng" }));

    expect(mockPut).toHaveBeenCalledWith("/orders/10/cancel");
    expect(await screen.findByText("Đã hủy")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hủy đơn hàng" })).not.toBeInTheDocument();
  });

  it("status != pending - KHÔNG hiện nút Hủy đơn hàng", async () => {
    mockOrderOutcomes(10, { ok: true, data: okResponse({ ...baseOrder, status: "confirmed" }) });
    render(<OrderDetailView orderId={10} />);

    await screen.findByText("Đơn hàng #10");
    expect(screen.queryByRole("button", { name: "Hủy đơn hàng" })).not.toBeInTheDocument();
  });

  it("nhận event SSE order_status ĐÚNG order_id đang xem -> tự fetch lại đơn", async () => {
    mockOrderOutcomes(
      10,
      { ok: true, data: okResponse(baseOrder) },
      { ok: true, data: okResponse({ ...baseOrder, status: "confirmed" }) },
    );
    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    act(() => {
      capturedOnOrderStatus?.({ order_id: 10, status: "confirmed", timestamp: "2026-08-02T00:00:00Z" });
    });

    await waitFor(() => expect(countCallsTo("/orders/10")).toBe(2));
    expect(await screen.findByText("Đã xác nhận")).toBeInTheDocument();
  });

  it("nhận event SSE order_status của đơn KHÁC -> KHÔNG fetch lại", async () => {
    mockOrderOutcomes(10, { ok: true, data: okResponse(baseOrder) });
    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    act(() => {
      capturedOnOrderStatus?.({ order_id: 999, status: "confirmed", timestamp: "2026-08-02T00:00:00Z" });
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(countCallsTo("/orders/10")).toBe(1);
  });

  describe("Khối 'Thanh toán' (task \"Quyết định và hoàn thiện thanh toán\")", () => {
    it("đơn KHÔNG pending & không có payment (VD delivered COD, 404) - KHÔNG hiện khối Thanh toán", async () => {
      mockOrderOutcomes(10, { ok: true, data: okResponse({ ...baseOrder, status: "delivered" }) });
      render(<OrderDetailView orderId={10} />);

      await screen.findByText("Đơn hàng #10");
      expect(screen.queryByText("Thanh toán")).not.toBeInTheDocument();
    });

    it("đơn pending chưa có payment (404) - hiện nút 'Thanh toán qua VNPay' (đường phục hồi #1); bấm gọi POST /payments/create, điều hướng cứng", async () => {
      const user = userEvent.setup();
      const originalLocation = window.location;
      // @ts-expect-error - test-only: jsdom location là accessor, phải xóa trước khi gán lại.
      delete window.location;
      // @ts-expect-error - test-only stub, chỉ cần field href.
      window.location = { href: "" };

      mockOrderOutcomes(10, { ok: true, data: okResponse(baseOrder) }); // payments -> 404 (chưa có Payment)
      mockPost.mockResolvedValue({
        data: { success: true, message: "", data: { payment_id: 2, order_id: 10, payment_url: "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=2A1" } },
      });

      render(<OrderDetailView orderId={10} />);
      await screen.findByText("Đơn hàng #10");

      // Nhãn "Thanh toán qua VNPay" (KHÔNG phải "Thanh toán lại") vì chưa có giao dịch nào.
      const payButton = await screen.findByRole("button", { name: "Thanh toán qua VNPay" });
      await user.click(payButton);

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/payments/create", { order_id: 10 }));
      expect(window.location.href).toBe("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=2A1");

      window.location = originalLocation;
    });

    it("payment status=success - hiện 'Đã thanh toán', KHÔNG có nút thanh toán, và ẩn cả nút Hủy đơn hàng (#4b)", async () => {
      mockOrderOutcomesWithPayment(10, paymentResponse("success"), { ok: true, data: okResponse(baseOrder) });
      render(<OrderDetailView orderId={10} />);

      await screen.findByText("Đơn hàng #10");
      expect(await screen.findByText("Đã thanh toán")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Thanh toán/ })).not.toBeInTheDocument();
      // Đơn pending nhưng ĐÃ thanh toán online -> nút Hủy bị ẩn (Backend chặn
      // 409, không hiện nút chỉ để nhận lỗi).
      expect(screen.queryByRole("button", { name: "Hủy đơn hàng" })).not.toBeInTheDocument();
    });

    it("payment status=failed - hiện 'Thanh toán thất bại' + nút thanh toán lại; bấm gọi đúng POST /payments/create, điều hướng cứng", async () => {
      const user = userEvent.setup();
      const originalLocation = window.location;
      // @ts-expect-error - test-only: jsdom location là accessor, phải xóa trước khi gán lại.
      delete window.location;
      // @ts-expect-error - test-only stub, chỉ cần field href.
      window.location = { href: "" };

      mockOrderOutcomesWithPayment(10, paymentResponse("failed"), { ok: true, data: okResponse(baseOrder) });
      mockPost.mockResolvedValue({
        data: { success: true, message: "", data: { payment_id: 1, order_id: 10, payment_url: "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=1" } },
      });

      render(<OrderDetailView orderId={10} />);
      await screen.findByText("Đơn hàng #10");

      expect(await screen.findByText("Thanh toán thất bại")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Thanh toán lại qua VNPay" }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/payments/create", { order_id: 10 }));
      expect(window.location.href).toBe("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=1");

      window.location = originalLocation;
    });

    it("thanh toán lại thất bại (VD 409 đã thanh toán ở tab khác) - hiện toast lỗi, KHÔNG điều hướng đi đâu", async () => {
      const user = userEvent.setup();
      mockOrderOutcomesWithPayment(10, paymentResponse("pending"), { ok: true, data: okResponse(baseOrder) });
      mockPost.mockRejectedValue(
        new AxiosError("Request failed with status code 409", "ERR_BAD_REQUEST", undefined, undefined, {
          status: 409,
          data: { success: false, message: "Đơn hàng đã ở trạng thái thanh toán \"success\"" },
        } as never),
      );

      render(<OrderDetailView orderId={10} />);
      await screen.findByText("Đơn hàng #10");
      await user.click(await screen.findByRole("button", { name: "Thanh toán lại qua VNPay" }));

      await waitFor(() => expect(mockToastError).toHaveBeenCalledWith('Đơn hàng đã ở trạng thái thanh toán "success"'));
    });
  });
});
