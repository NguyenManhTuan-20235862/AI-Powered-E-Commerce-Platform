import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OrderCard } from "@/components/order/OrderCard";
import type { Order } from "@/types/order";

const mockPut = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    put: (...args: unknown[]) => mockPut(...args),
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
  note: null,
  items: [
    { id: 1, product_id: 1, product_name: "Bình gốm", quantity: 2, price_at_purchase: "150000" },
  ],
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

describe("OrderCard (task 4.3.3) - nút Hủy đơn", () => {
  beforeEach(() => {
    vi.spyOn(window, "confirm");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockPut.mockReset();
  });

  it("CHỈ hiện nút Hủy đơn khi status = pending", () => {
    render(<OrderCard order={baseOrder} onCancelled={vi.fn()} />);
    expect(screen.getByText("Hủy đơn")).toBeInTheDocument();
  });

  it("KHÔNG hiện nút Hủy đơn khi status = confirmed", () => {
    render(<OrderCard order={{ ...baseOrder, status: "confirmed" }} onCancelled={vi.fn()} />);
    expect(screen.queryByText("Hủy đơn")).not.toBeInTheDocument();
  });

  it("KHÔNG hiện nút Hủy đơn khi status = delivered/cancelled", () => {
    const { rerender } = render(<OrderCard order={{ ...baseOrder, status: "delivered" }} onCancelled={vi.fn()} />);
    expect(screen.queryByText("Hủy đơn")).not.toBeInTheDocument();
    rerender(<OrderCard order={{ ...baseOrder, status: "cancelled" }} onCancelled={vi.fn()} />);
    expect(screen.queryByText("Hủy đơn")).not.toBeInTheDocument();
  });

  it("bấm Hủy đơn nhưng KHÔNG xác nhận confirm() -> KHÔNG gọi API", async () => {
    const user = userEvent.setup();
    vi.mocked(window.confirm).mockReturnValue(false);
    const onCancelled = vi.fn();
    render(<OrderCard order={baseOrder} onCancelled={onCancelled} />);

    await user.click(screen.getByText("Hủy đơn"));

    expect(window.confirm).toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
    expect(onCancelled).not.toHaveBeenCalled();
  });

  it("bấm Hủy đơn và XÁC NHẬN confirm() -> gọi đúng PUT /orders/{id}/cancel, báo callback", async () => {
    const user = userEvent.setup();
    vi.mocked(window.confirm).mockReturnValue(true);
    mockPut.mockResolvedValue({ data: { success: true, message: "Đã hủy đơn hàng", data: { ...baseOrder, status: "cancelled" } } });
    const onCancelled = vi.fn();
    render(<OrderCard order={baseOrder} onCancelled={onCancelled} />);

    await user.click(screen.getByText("Hủy đơn"));

    await waitFor(() => expect(mockPut).toHaveBeenCalledWith("/orders/10/cancel"));
    await waitFor(() => expect(onCancelled).toHaveBeenCalled());
  });
});
