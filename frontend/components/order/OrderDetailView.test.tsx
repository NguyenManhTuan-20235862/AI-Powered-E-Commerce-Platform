import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OrderDetailView } from "@/components/order/OrderDetailView";
import type { OrderStatusEvent } from "@/types/notification";
import type { Order } from "@/types/order";

const mockGet = vi.fn();
const mockPut = vi.fn();
const replaceMock = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    put: (...args: unknown[]) => mockPut(...args),
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

describe("OrderDetailView (hoàn thiện /orders/[id])", () => {
  beforeEach(() => {
    vi.spyOn(window, "confirm");
    capturedOnOrderStatus = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPut.mockReset();
    replaceMock.mockReset();
    retryStreamMock.mockReset();
  });

  it("hiện 'Đang tải...' trước khi fetch xong", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // chưa bao giờ resolve
    render(<OrderDetailView orderId={10} />);
    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
  });

  it("fetch thành công - hiện đủ trạng thái, snapshot sản phẩm, tổng tiền, người nhận, ghi chú, thời gian", async () => {
    mockGet.mockResolvedValue(okResponse(baseOrder));
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
    mockGet.mockRejectedValue(httpError(403));
    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Bạn không có quyền xem đơn hàng này.")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("404 - hiện thông báo không tìm thấy đơn hàng", async () => {
    mockGet.mockRejectedValue(httpError(404));
    render(<OrderDetailView orderId={999} />);

    expect(await screen.findByText("Không tìm thấy đơn hàng này.")).toBeInTheDocument();
  });

  it("lỗi mạng - hiện thông báo + nút Thử lại, bấm Thử lại gọi lại API", async () => {
    const user = userEvent.setup();
    mockGet.mockRejectedValueOnce(networkError());
    mockGet.mockResolvedValueOnce(okResponse(baseOrder));

    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và thử lại.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(await screen.findByText("Đơn hàng #10")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it("lỗi 500 - hiện message thật từ Backend + nút Thử lại", async () => {
    mockGet.mockRejectedValue(httpError(500, "Lỗi hệ thống, vui lòng thử lại sau"));
    render(<OrderDetailView orderId={10} />);

    expect(await screen.findByText("Lỗi hệ thống, vui lòng thử lại sau")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeInTheDocument();
  });

  it("status=pending - hiện nút Hủy đơn hàng; xác nhận confirm() -> PUT /orders/{id}/cancel, cập nhật lại trạng thái hiển thị", async () => {
    const user = userEvent.setup();
    vi.mocked(window.confirm).mockReturnValue(true);
    mockGet.mockResolvedValue(okResponse(baseOrder));
    mockPut.mockResolvedValue(okResponse({ ...baseOrder, status: "cancelled" }));

    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    await user.click(screen.getByRole("button", { name: "Hủy đơn hàng" }));

    expect(mockPut).toHaveBeenCalledWith("/orders/10/cancel");
    expect(await screen.findByText("Đã hủy")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hủy đơn hàng" })).not.toBeInTheDocument();
  });

  it("status != pending - KHÔNG hiện nút Hủy đơn hàng", async () => {
    mockGet.mockResolvedValue(okResponse({ ...baseOrder, status: "confirmed" }));
    render(<OrderDetailView orderId={10} />);

    await screen.findByText("Đơn hàng #10");
    expect(screen.queryByRole("button", { name: "Hủy đơn hàng" })).not.toBeInTheDocument();
  });

  it("nhận event SSE order_status ĐÚNG order_id đang xem -> tự fetch lại đơn", async () => {
    mockGet.mockResolvedValueOnce(okResponse(baseOrder));
    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    mockGet.mockResolvedValueOnce(okResponse({ ...baseOrder, status: "confirmed" }));
    act(() => {
      capturedOnOrderStatus?.({ order_id: 10, status: "confirmed", timestamp: "2026-08-02T00:00:00Z" });
    });

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Đã xác nhận")).toBeInTheDocument();
  });

  it("nhận event SSE order_status của đơn KHÁC -> KHÔNG fetch lại", async () => {
    mockGet.mockResolvedValue(okResponse(baseOrder));
    render(<OrderDetailView orderId={10} />);
    await screen.findByText("Đơn hàng #10");

    act(() => {
      capturedOnOrderStatus?.({ order_id: 999, status: "confirmed", timestamp: "2026-08-02T00:00:00Z" });
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mockGet).toHaveBeenCalledTimes(1);
  });
});
