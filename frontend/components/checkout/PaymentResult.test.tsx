import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PaymentResult } from "@/components/checkout/PaymentResult";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockToastError = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: vi.fn(),
  },
}));

// Module-level, có thể gán lại từng test - cùng pattern OrdersView.test.tsx.
let currentSearchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => currentSearchParams,
}));

const orderResponse = {
  data: {
    success: true,
    message: "",
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
};

function paymentResponse(status: "pending" | "success" | "failed" | "refunded") {
  return {
    data: {
      success: true,
      message: "",
      data: {
        order_id: 42,
        payment_method: "vnpay",
        transaction_id: status === "success" ? "14000123" : null,
        amount: "300000",
        status,
        created_at: "2026-08-09T00:00:00",
        updated_at: "2026-08-09T00:00:00",
      },
    },
  };
}

function mockRoutes(paymentStatus: "pending" | "success" | "failed" | "refunded") {
  mockGet.mockImplementation((url: string) => {
    if (url === "/orders/42") return Promise.resolve(orderResponse);
    if (url === "/payments/42/status") return Promise.resolve(paymentResponse(paymentStatus));
    throw new Error(`unexpected GET url: ${url}`);
  });
}

describe("PaymentResult (task \"Quyết định và hoàn thiện thanh toán\")", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPost.mockReset();
    mockToastError.mockReset();
    currentSearchParams = new URLSearchParams();
  });

  it("thiếu order_id - hiện thông báo không xác minh được, KHÔNG gọi API nào", async () => {
    currentSearchParams = new URLSearchParams({ status: "invalid" });
    render(<PaymentResult />);

    expect(await screen.findByText("Không thể xác minh giao dịch")).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("status=success (đã xác minh thật qua fetch lại, KHÔNG tin thẳng query param) - hiện UI thành công, KHÔNG có nút thanh toán lại", async () => {
    currentSearchParams = new URLSearchParams({ order_id: "42", status: "success" });
    mockRoutes("success");
    render(<PaymentResult />);

    expect(await screen.findByText("Thanh toán thành công!")).toBeInTheDocument();
    expect(screen.getByText("300.000 ₫")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Thanh toán lại/ })).not.toBeInTheDocument();
  });

  it("payment thật là failed (dù query param optimistic khác) - hiện UI thất bại + nút thanh toán lại", async () => {
    currentSearchParams = new URLSearchParams({ order_id: "42", status: "failed" });
    mockRoutes("failed");
    render(<PaymentResult />);

    expect(await screen.findByText("Thanh toán thất bại")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thanh toán lại qua VNPay" })).toBeInTheDocument();
  });

  it("payment đang pending - hiện UI chờ xác nhận + vẫn có nút thanh toán lại", async () => {
    currentSearchParams = new URLSearchParams({ order_id: "42", status: "success" });
    mockRoutes("pending");
    render(<PaymentResult />);

    expect(await screen.findByText("Đang chờ xác nhận thanh toán")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thanh toán lại qua VNPay" })).toBeInTheDocument();
  });

  it("bấm 'Thanh toán lại qua VNPay' - gọi đúng POST /payments/create, điều hướng cứng sang payment_url", async () => {
    const user = userEvent.setup();
    const originalLocation = window.location;
    // @ts-expect-error - test-only: jsdom location là accessor, phải xóa trước khi gán lại.
    delete window.location;
    // @ts-expect-error - test-only stub, chỉ cần field href.
    window.location = { href: "" };

    currentSearchParams = new URLSearchParams({ order_id: "42", status: "failed" });
    mockRoutes("failed");
    mockPost.mockResolvedValue({
      data: { success: true, message: "", data: { payment_id: 2, order_id: 42, payment_url: "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=2" } },
    });

    render(<PaymentResult />);
    await screen.findByText("Thanh toán thất bại");

    await user.click(screen.getByRole("button", { name: "Thanh toán lại qua VNPay" }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/payments/create", { order_id: 42 }));
    expect(window.location.href).toBe("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=2");

    window.location = originalLocation;
  });

  it("fetch lỗi - hiện thông báo lỗi chung + nút Thử lại", async () => {
    currentSearchParams = new URLSearchParams({ order_id: "42", status: "success" });
    mockGet.mockRejectedValue(new Error("network down"));
    render(<PaymentResult />);

    expect(await screen.findByText("Không tải được kết quả thanh toán.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeInTheDocument();
  });
});
