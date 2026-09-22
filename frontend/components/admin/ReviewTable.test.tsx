import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewTable } from "@/components/admin/ReviewTable";
import type { AdminReview } from "@/types/review";

const mockDelete = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

const activeReview: AdminReview = {
  id: "rev-1",
  product_id: 1,
  product_name: "Bình gốm thủ công",
  user_id: 10,
  user_name: "Trần Thị B",
  order_id: 100,
  rating: 5,
  comment: "Rất tốt",
  images: null,
  is_verified_purchase: true,
  is_deleted: false,
  created_at: "2026-08-01T00:00:00",
  updated_at: null,
};

const deletedReview: AdminReview = {
  ...activeReview,
  id: "rev-2",
  product_name: "Sổ tay lập kế hoạch",
  user_name: "Lê Văn C",
  comment: "Nội dung vi phạm",
  is_deleted: true,
};

const noopProps = {
  isLoading: false,
  isDeleted: "" as const,
  onStatusChange: vi.fn(),
  page: 1,
  totalPages: 1,
  total: 2,
  pageSize: 20,
  onPageChange: vi.fn(),
  onDeleted: vi.fn(),
};

describe("ReviewTable (task Hoàn thiện review sản phẩm)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockDelete.mockReset();
  });

  it("hiện đủ thông tin: sản phẩm, người đánh giá, nhận xét, trạng thái", () => {
    render(<ReviewTable {...noopProps} reviews={[activeReview, deletedReview]} />);
    const table = within(screen.getByRole("table"));

    expect(table.getByText("Bình gốm thủ công")).toBeInTheDocument();
    expect(table.getByText("Trần Thị B")).toBeInTheDocument();
    expect(table.getByText("Rất tốt")).toBeInTheDocument();
    expect(table.getByText("Đang hiển thị")).toBeInTheDocument();
    expect(table.getByText("Đã xóa")).toBeInTheDocument();
  });

  it("review ĐÃ xóa - KHÔNG hiện nút Xóa, chỉ hiện '—'", () => {
    render(<ReviewTable {...noopProps} reviews={[deletedReview]} />);
    const table = within(screen.getByRole("table"));

    expect(table.queryByRole("button", { name: "Xóa" })).not.toBeInTheDocument();
    expect(table.getByText("—")).toBeInTheDocument();
  });

  it("review ĐANG hiển thị - hiện nút Xóa", () => {
    render(<ReviewTable {...noopProps} reviews={[activeReview]} />);
    expect(screen.getByRole("button", { name: "Xóa" })).toBeInTheDocument();
  });

  it("bấm Xóa nhưng KHÔNG xác nhận confirm() -> KHÔNG gọi API", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<ReviewTable {...noopProps} reviews={[activeReview]} />);

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(mockDelete).not.toHaveBeenCalled();
  });

  it("bấm Xóa và XÁC NHẬN confirm() -> gọi đúng DELETE /reviews/{id}, báo callback", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDelete.mockResolvedValue({ data: { success: true, message: "Đã xóa review" } });
    const onDeleted = vi.fn();
    render(<ReviewTable {...noopProps} reviews={[activeReview]} onDeleted={onDeleted} />);

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("/reviews/rev-1"));
    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith("rev-1"));
  });

  it("đổi filter trạng thái gọi đúng callback", async () => {
    const user = userEvent.setup();
    const onStatusChange = vi.fn();
    render(<ReviewTable {...noopProps} reviews={[]} onStatusChange={onStatusChange} />);

    await user.selectOptions(screen.getByDisplayValue("Tất cả trạng thái"), "true");
    expect(onStatusChange).toHaveBeenCalledWith("true");
  });
});
