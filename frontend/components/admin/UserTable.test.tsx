import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserTable } from "@/components/admin/UserTable";
import type { AdminUser } from "@/types/user";

const mockPut = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

const adminUser: AdminUser = {
  id: 1,
  email: "admin@example.com",
  full_name: "Nguyễn Văn A",
  phone: "0901234567",
  role: "admin",
  address: null,
  is_active: true,
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

const activeCustomer: AdminUser = {
  id: 2,
  email: "customer1@example.com",
  full_name: "Trần Thị B",
  phone: "0912345678",
  role: "customer",
  address: null,
  is_active: true,
  created_at: "2026-08-02T00:00:00",
  updated_at: "2026-08-02T00:00:00",
};

const lockedCustomer: AdminUser = {
  id: 3,
  email: "customer2@example.com",
  full_name: "Lê Văn C",
  phone: "0923456789",
  role: "customer",
  address: null,
  is_active: false,
  created_at: "2026-08-03T00:00:00",
  updated_at: "2026-08-03T00:00:00",
};

const noopProps = {
  isLoading: false,
  search: "",
  onSearchChange: vi.fn(),
  role: "" as const,
  onRoleChange: vi.fn(),
  isActive: "" as const,
  onStatusChange: vi.fn(),
  page: 1,
  totalPages: 1,
  onPageChange: vi.fn(),
  onChanged: vi.fn(),
};

describe("UserTable (Quản lý người dùng Admin) - badge + hành động khóa/mở khóa", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockPut.mockReset();
  });

  it("hiển thị đúng badge vai trò và trạng thái cho từng dòng", () => {
    render(<UserTable {...noopProps} users={[adminUser, activeCustomer, lockedCustomer]} />);
    const table = within(screen.getByRole("table"));

    expect(table.getByText("Admin")).toBeInTheDocument();
    expect(table.getAllByText("Customer")).toHaveLength(2);
    expect(table.getAllByText("Đang hoạt động")).toHaveLength(2); // admin + activeCustomer
    expect(table.getByText("Đã khóa")).toBeInTheDocument();
  });

  it("ẨN nút Khóa/Mở khóa ở hàng role=admin - chỉ hiện dấu '—'", () => {
    render(<UserTable {...noopProps} users={[adminUser]} />);
    const table = within(screen.getByRole("table"));

    expect(table.queryByRole("button", { name: "Khóa" })).not.toBeInTheDocument();
    expect(table.queryByRole("button", { name: "Mở khóa" })).not.toBeInTheDocument();
    expect(table.getByText("—")).toBeInTheDocument();
  });

  it("HIỆN nút 'Khóa' cho customer đang hoạt động, 'Mở khóa' cho customer đã khóa", () => {
    render(<UserTable {...noopProps} users={[activeCustomer, lockedCustomer]} />);

    expect(screen.getByRole("button", { name: "Khóa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở khóa" })).toBeInTheDocument();
  });

  it("bấm 'Khóa' nhưng KHÔNG xác nhận confirm() -> KHÔNG gọi API", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<UserTable {...noopProps} users={[activeCustomer]} />);

    await user.click(screen.getByRole("button", { name: "Khóa" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
  });

  it("bấm 'Khóa' và XÁC NHẬN confirm() -> gọi đúng PUT /users/{id}/status với is_active=false", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockPut.mockResolvedValue({ data: { success: true, message: "ok", data: { ...activeCustomer, is_active: false } } });
    const onChanged = vi.fn();
    render(<UserTable {...noopProps} users={[activeCustomer]} onChanged={onChanged} />);

    await user.click(screen.getByRole("button", { name: "Khóa" }));

    await waitFor(() => expect(mockPut).toHaveBeenCalledWith("/users/2/status", { is_active: false }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("bấm 'Mở khóa' KHÔNG cần confirm() - gọi thẳng PUT với is_active=true", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm");
    mockPut.mockResolvedValue({ data: { success: true, message: "ok", data: { ...lockedCustomer, is_active: true } } });
    const onChanged = vi.fn();
    render(<UserTable {...noopProps} users={[lockedCustomer]} onChanged={onChanged} />);

    await user.click(screen.getByRole("button", { name: "Mở khóa" }));

    expect(confirmSpy).not.toHaveBeenCalled();
    await waitFor(() => expect(mockPut).toHaveBeenCalledWith("/users/3/status", { is_active: true }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("gõ vào ô search gọi onSearchChange với đúng giá trị", async () => {
    const user = userEvent.setup();
    const onSearchChange = vi.fn();
    render(<UserTable {...noopProps} users={[]} onSearchChange={onSearchChange} />);

    await user.type(screen.getByPlaceholderText("Tìm theo tên hoặc email..."), "an");

    expect(onSearchChange).toHaveBeenCalled();
  });

  it("đổi filter vai trò/trạng thái gọi đúng callback", async () => {
    const user = userEvent.setup();
    const onRoleChange = vi.fn();
    const onStatusChange = vi.fn();
    render(<UserTable {...noopProps} users={[]} onRoleChange={onRoleChange} onStatusChange={onStatusChange} />);

    await user.selectOptions(screen.getByDisplayValue("Tất cả vai trò"), "admin");
    expect(onRoleChange).toHaveBeenCalledWith("admin");

    await user.selectOptions(screen.getByDisplayValue("Tất cả trạng thái"), "false");
    expect(onStatusChange).toHaveBeenCalledWith("false");
  });
});
