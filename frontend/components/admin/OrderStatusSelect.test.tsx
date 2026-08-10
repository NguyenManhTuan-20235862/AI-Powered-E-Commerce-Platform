import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OrderStatusSelect } from "@/components/admin/OrderStatusSelect";
import type { Order } from "@/types/order";

const mockPut = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

const baseOrder: Order = {
  id: 5,
  user_id: 1,
  status: "pending",
  total_amount: "300000",
  shipping_name: "Nguyễn Văn A",
  shipping_address: "123 Đường ABC",
  shipping_phone: "0912345678",
  note: null,
  items: [],
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

function optionValues(select: HTMLElement): string[] {
  return within(select)
    .getAllByRole("option")
    .map((opt) => (opt as HTMLOptionElement).value);
}

// task 4.4.2 - QUAN TRỌNG NHẤT của task: dropdown CHỈ được hiện đúng các
// lựa chọn hợp lệ theo VALID_STATUS_TRANSITIONS thật (backend/app/services/
// order_service.py) của TRẠNG THÁI HIỆN TẠI - test riêng CẢ 5 trạng thái đầu
// vào, không gộp chung 1 test để mỗi trường hợp fail độc lập, dễ định vị lỗi.
describe("OrderStatusSelect (task 4.4.2) - option list theo VALID_STATUS_TRANSITIONS", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockPut.mockReset();
  });

  it("status=pending -> chỉ pending/confirmed/cancelled, KHÔNG disable", () => {
    render(<OrderStatusSelect order={{ ...baseOrder, status: "pending" }} onChanged={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(optionValues(select)).toEqual(["pending", "confirmed", "cancelled"]);
    expect(select).toBeEnabled();
  });

  it("status=confirmed -> chỉ confirmed/shipping/cancelled, KHÔNG disable", () => {
    render(<OrderStatusSelect order={{ ...baseOrder, status: "confirmed" }} onChanged={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(optionValues(select)).toEqual(["confirmed", "shipping", "cancelled"]);
    expect(select).toBeEnabled();
  });

  it("status=shipping -> chỉ shipping/delivered, KHÔNG disable", () => {
    render(<OrderStatusSelect order={{ ...baseOrder, status: "shipping" }} onChanged={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(optionValues(select)).toEqual(["shipping", "delivered"]);
    expect(select).toBeEnabled();
  });

  it("status=delivered -> CHỈ delivered, disable HOÀN TOÀN (terminal)", () => {
    render(<OrderStatusSelect order={{ ...baseOrder, status: "delivered" }} onChanged={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(optionValues(select)).toEqual(["delivered"]);
    expect(select).toBeDisabled();
  });

  it("status=cancelled -> CHỈ cancelled, disable HOÀN TOÀN (terminal)", () => {
    render(<OrderStatusSelect order={{ ...baseOrder, status: "cancelled" }} onChanged={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(optionValues(select)).toEqual(["cancelled"]);
    expect(select).toBeDisabled();
  });

  it("chọn trạng thái mới nhưng KHÔNG xác nhận confirm() -> KHÔNG gọi API, giữ nguyên giá trị", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const onChanged = vi.fn();
    render(<OrderStatusSelect order={{ ...baseOrder, status: "pending" }} onChanged={onChanged} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;

    await user.selectOptions(select, "confirmed");

    expect(window.confirm).toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
    expect(onChanged).not.toHaveBeenCalled();
    expect(select.value).toBe("pending");
  });

  it("chọn trạng thái mới và XÁC NHẬN confirm() -> gọi đúng PUT /orders/{id}/status với status mới", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockPut.mockResolvedValue({
      data: { success: true, message: "ok", data: { ...baseOrder, status: "confirmed" } },
    });
    const onChanged = vi.fn();
    render(<OrderStatusSelect order={{ ...baseOrder, status: "pending" }} onChanged={onChanged} />);
    const select = screen.getByRole("combobox");

    await user.selectOptions(select, "confirmed");

    await waitFor(() => expect(mockPut).toHaveBeenCalledWith("/orders/5/status", { status: "confirmed" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });
});
