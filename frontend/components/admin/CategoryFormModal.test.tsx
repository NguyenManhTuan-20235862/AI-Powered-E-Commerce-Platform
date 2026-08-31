import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CategoryFormModal } from "@/components/admin/CategoryFormModal";
import type { Category } from "@/types/category";

const mockPost = vi.fn();
const mockPut = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

const categories: Category[] = [
  { id: 1, name: "Điện tử", slug: "dien-tu", description: null, parent_id: null, created_at: "2026-08-01T00:00:00" },
  { id: 2, name: "Điện thoại", slug: "dien-thoai", description: null, parent_id: 1, created_at: "2026-08-01T00:00:00" },
];

const existingCategory: Category = {
  id: 2,
  name: "Điện thoại",
  slug: "dien-thoai",
  description: "Mô tả cũ",
  parent_id: 1,
  created_at: "2026-08-01T00:00:00",
};

describe("CategoryFormModal (CRUD Category Admin)", () => {
  beforeEach(() => {
    mockPost.mockResolvedValue({
      data: { success: true, message: "Tạo danh mục thành công", data: { ...existingCategory, id: 99 } },
    });
    mockPut.mockResolvedValue({ data: { success: true, message: "", data: existingCategory } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("hiện lỗi validate khi bỏ trống tên rồi submit", async () => {
    const user = userEvent.setup();
    render(<CategoryFormModal isOpen onClose={vi.fn()} category={null} categories={categories} onSaved={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));

    expect(await screen.findByText("Vui lòng nhập tên danh mục.")).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("dropdown 'Danh mục cha' LOẠI TRỪ chính category đang sửa khỏi lựa chọn", () => {
    render(
      <CategoryFormModal
        isOpen
        onClose={vi.fn()}
        category={existingCategory}
        categories={categories}
        onSaved={vi.fn()}
      />,
    );

    const select = screen.getByLabelText("Danh mục cha") as HTMLSelectElement;
    const optionValues = Array.from(select.options).map((opt) => opt.value);
    expect(optionValues).toEqual(["", "1"]); // "Không có" + "Điện tử" - KHÔNG có "2" (chính nó)
  });

  it("KHÔNG có field slug nào trong form (ẩn hoàn toàn khỏi Admin)", () => {
    render(<CategoryFormModal isOpen onClose={vi.fn()} category={null} categories={categories} onSaved={vi.fn()} />);
    expect(screen.queryByLabelText(/slug/i)).not.toBeInTheDocument();
  });

  it("chế độ TẠO MỚI - submit hợp lệ gọi đúng POST /categories, không gọi PUT", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const onClose = vi.fn();
    render(<CategoryFormModal isOpen onClose={onClose} category={null} categories={categories} onSaved={onSaved} />);

    await user.type(screen.getByLabelText("Tên danh mục *"), "Đồ chơi");
    await user.selectOptions(screen.getByLabelText("Danh mục cha"), "1");

    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith("/categories", {
        name: "Đồ chơi",
        description: undefined,
        parent_id: 1,
      }),
    );
    expect(mockPut).not.toHaveBeenCalled();
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(onClose).toHaveBeenCalled();
  });

  it("tạo mới không chọn danh mục cha - gửi parent_id=undefined (không phải 0/rỗng)", async () => {
    const user = userEvent.setup();
    render(<CategoryFormModal isOpen onClose={vi.fn()} category={null} categories={categories} onSaved={vi.fn()} />);

    await user.type(screen.getByLabelText("Tên danh mục *"), "Sách");
    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith("/categories", {
        name: "Sách",
        description: undefined,
        parent_id: undefined,
      }),
    );
  });

  it("chế độ SỬA - pre-fill đúng giá trị hiện tại, submit gọi đúng PUT /categories/{id}", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    render(
      <CategoryFormModal
        isOpen
        onClose={vi.fn()}
        category={existingCategory}
        categories={categories}
        onSaved={onSaved}
      />,
    );

    expect(await screen.findByDisplayValue("Điện thoại")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Mô tả cũ")).toBeInTheDocument();

    const nameInput = screen.getByLabelText("Tên danh mục *");
    await user.clear(nameInput);
    await user.type(nameInput, "Điện thoại di động");

    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));

    await waitFor(() =>
      expect(mockPut).toHaveBeenCalledWith("/categories/2", {
        name: "Điện thoại di động",
        description: "Mô tả cũ",
        parent_id: 1,
      }),
    );
    expect(mockPost).not.toHaveBeenCalled();
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it("sửa - bỏ chọn danh mục cha (chuyển về 'Không có') gửi parent_id=null (khác undefined)", async () => {
    const user = userEvent.setup();
    render(
      <CategoryFormModal
        isOpen
        onClose={vi.fn()}
        category={existingCategory}
        categories={categories}
        onSaved={vi.fn()}
      />,
    );

    await user.selectOptions(screen.getByLabelText("Danh mục cha"), "");
    await user.click(screen.getByRole("button", { name: "Lưu danh mục" }));

    await waitFor(() =>
      expect(mockPut).toHaveBeenCalledWith("/categories/2", {
        name: "Điện thoại",
        description: "Mô tả cũ",
        parent_id: null,
      }),
    );
  });
});
