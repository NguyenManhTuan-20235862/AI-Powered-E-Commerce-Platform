import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserDetailModal } from "@/components/admin/UserDetailModal";
import type { Order } from "@/types/order";
import type { AdminUser } from "@/types/user";

const mockGet = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

const sampleUser: AdminUser = {
  id: 5,
  email: "customer5@example.com",
  full_name: "Trần Thị B",
  phone: "0912345678",
  address: "123 Đường ABC",
  role: "customer",
  is_active: true,
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

const sampleOrder: Order = {
  id: 20,
  user_id: 5,
  status: "pending",
  total_amount: "150000",
  shipping_name: "Trần Thị B",
  shipping_address: "123 Đường ABC",
  shipping_phone: "0912345678",
  note: null,
  items: [{ id: 1, product_id: 1, product_name: "Bình gốm", quantity: 1, price_at_purchase: "150000" }],
  created_at: "2026-08-05T00:00:00",
  updated_at: "2026-08-05T00:00:00",
};

function userResponse(user: AdminUser) {
  return { data: { success: true, message: "", data: user } };
}

function ordersResponse(items: Order[], totalPages = 1) {
  return { data: { success: true, message: "", data: { items, total: items.length, page: 1, page_size: 5, total_pages: totalPages } } };
}

describe("UserDetailModal (task Hoàn thiện quản lý tài khoản Admin)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
  });

  it("fetch GET /users/{id} VÀ GET /orders/admin?user_id={id} khi mở, hiện đủ thông tin", async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.resolve(userResponse(sampleUser));
      if (url === "/orders/admin") return Promise.resolve(ordersResponse([sampleOrder]));
      throw new Error(`unexpected url: ${url}`);
    });

    render(<UserDetailModal userId={5} onClose={vi.fn()} />);

    expect(await screen.findByText("Trần Thị B")).toBeInTheDocument();
    expect(screen.getByText("customer5@example.com")).toBeInTheDocument();
    expect(screen.getByText("0912345678")).toBeInTheDocument();
    expect(screen.getByText("123 Đường ABC")).toBeInTheDocument();
    expect(screen.getByText("Đang hoạt động")).toBeInTheDocument();

    expect(await screen.findByText("#20")).toBeInTheDocument();
    expect(screen.getByText("150.000 ₫")).toBeInTheDocument();

    expect(mockGet).toHaveBeenCalledWith("/users/5");
    expect(mockGet).toHaveBeenCalledWith(
      "/orders/admin",
      expect.objectContaining({ params: { user_id: 5, page: 1, page_size: 5 } }),
    );
  });

  it("user chưa có đơn hàng nào - hiện thông báo rỗng, KHÔNG hiện lỗi", async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.resolve(userResponse(sampleUser));
      return Promise.resolve(ordersResponse([]));
    });

    render(<UserDetailModal userId={5} onClose={vi.fn()} />);

    expect(await screen.findByText("Người dùng chưa có đơn hàng nào.")).toBeInTheDocument();
  });

  it("lỗi tải thông tin user - hiện thông báo lỗi", async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.reject(new Error("network down"));
      return Promise.resolve(ordersResponse([]));
    });

    render(<UserDetailModal userId={5} onClose={vi.fn()} />);

    expect(await screen.findByText("Không thể tải thông tin người dùng.")).toBeInTheDocument();
  });

  it("bấm nút Đóng gọi onClose", async () => {
    const user = userEvent.setup();
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.resolve(userResponse(sampleUser));
      return Promise.resolve(ordersResponse([]));
    });
    const onClose = vi.fn();
    render(<UserDetailModal userId={5} onClose={onClose} />);
    await screen.findByText("Trần Thị B");

    await user.click(screen.getByRole("button", { name: "Đóng" }));

    expect(onClose).toHaveBeenCalled();
  });

  it("bấm nền tối (ngoài dialog) GỌI onClose, bấm TRONG dialog KHÔNG gọi onClose", async () => {
    const user = userEvent.setup();
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.resolve(userResponse(sampleUser));
      return Promise.resolve(ordersResponse([]));
    });
    const onClose = vi.fn();
    render(<UserDetailModal userId={5} onClose={onClose} />);
    await screen.findByText("Trần Thị B");

    const backdrop = screen.getByRole("dialog").parentElement;
    if (!backdrop) throw new Error("backdrop element not found");
    await user.click(backdrop);
    expect(onClose).toHaveBeenCalled();

    onClose.mockClear();
    await user.click(screen.getByText("Chi tiết người dùng"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("nhiều trang đơn hàng - bấm 'Trang sau' gọi lại API với page=2", async () => {
    const user = userEvent.setup();
    mockGet.mockImplementation((url: string) => {
      if (url === "/users/5") return Promise.resolve(userResponse(sampleUser));
      return Promise.resolve(ordersResponse([sampleOrder], 2));
    });

    render(<UserDetailModal userId={5} onClose={vi.fn()} />);
    await screen.findByText("#20");

    await user.click(screen.getByRole("button", { name: "Trang sau" }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith(
        "/orders/admin",
        expect.objectContaining({ params: { user_id: 5, page: 2, page_size: 5 } }),
      ),
    );
  });
});
