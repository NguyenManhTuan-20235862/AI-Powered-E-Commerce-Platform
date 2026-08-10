import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrderStatusBadge } from "@/components/order/OrderStatusBadge";
import type { OrderStatus } from "@/types/order";

// Task 4.3.3 - đảm bảo map ĐÚNG nhãn + màu cho từng trạng thái thật của
// Backend (OrderStatus enum) - tránh lệch nếu sau này sửa nhầm 1 trong 5.
describe("OrderStatusBadge (task 4.3.3)", () => {
  const cases: { status: OrderStatus; label: string; classFragment: string }[] = [
    { status: "pending", label: "Chờ xác nhận", classFragment: "bg-primary-100" },
    { status: "confirmed", label: "Đã xác nhận", classFragment: "bg-primary-300" },
    { status: "shipping", label: "Đang giao", classFragment: "bg-primary" },
    { status: "delivered", label: "Đã giao", classFragment: "bg-secondary" },
    { status: "cancelled", label: "Đã hủy", classFragment: "bg-error-container" },
  ];

  it.each(cases)("hiện đúng nhãn + màu cho trạng thái $status", ({ status, label, classFragment }) => {
    render(<OrderStatusBadge status={status} />);
    const badge = screen.getByText(label);
    expect(badge).toHaveClass(classFragment);
  });
});
