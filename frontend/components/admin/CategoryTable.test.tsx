import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CategoryTable } from "@/components/admin/CategoryTable";
import type { Category } from "@/types/category";

function makeApiError(status: number, message: string): AxiosError {
  return new AxiosError(`Request failed with status code ${status}`, "ERR_BAD_REQUEST", undefined, undefined, {
    status,
    data: { success: false, message },
  } as never);
}

const mockDelete = vi.fn();
const mockToastError = vi.fn();

// KHÔNG có test nào trong dự án từng render <Toaster/> thật để đọc nội dung
// DOM (sonner cần 1 <Toaster/> mounted mới thực sự render ra body - test
// component đơn lẻ ở đây không có) - mock thẳng `sonner` để assert ĐÚNG
// message được truyền vào `toast.error()`, đáng tin cậy hơn hẳn cố đọc
// `document.body.textContent` (sẽ luôn rỗng vì không có Toaster nào mounted).
vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: vi.fn(),
  },
}));

vi.mock("@/lib/axios", () => ({
  api: {
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

const parentCategory: Category = {
  id: 1,
  name: "Điện tử",
  slug: "dien-tu",
  description: "Thiết bị điện tử, phụ kiện công nghệ cho công việc và giải trí, đủ dài để bị rút gọn khi hiển thị",
  parent_id: null,
  created_at: "2026-08-01T00:00:00",
};

const childCategory: Category = {
  id: 2,
  name: "Điện thoại",
  slug: "dien-thoai",
  description: null,
  parent_id: 1,
  created_at: "2026-08-01T00:00:00",
};

const noopProps = {
  isLoading: false,
  onEdit: vi.fn(),
  onChanged: vi.fn(),
};

describe("CategoryTable (CRUD Category Admin)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    mockDelete.mockReset();
    mockToastError.mockReset();
  });

  it("hiển thị đúng tên/slug/mô tả rút gọn/tên danh mục cha", () => {
    render(<CategoryTable {...noopProps} categories={[parentCategory, childCategory]} />);
    const table = within(screen.getByRole("table"));

    // "Điện tử" xuất hiện ĐÚNG 2 lần có chủ đích: tên của chính dòng cha, VÀ
    // tên cha hiển thị ở cột "Danh mục cha" của dòng con - dùng getAllByText,
    // không phải trùng lặp ngoài ý muốn.
    expect(table.getAllByText("Điện tử")).toHaveLength(2);
    expect(table.getByText("dien-tu")).toBeInTheDocument();
    // Mô tả > 60 ký tự phải bị rút gọn kèm dấu "…" - chỉ khớp phần đầu chắc
    // chắn nằm trong 60 ký tự, không đoán chính xác điểm cắt (dễ lệch off-by-few).
    expect(table.getByText(/^Thiết bị điện tử, phụ kiện công nghệ.*…$/)).toBeInTheDocument();

    // Điện thoại (con) hiển thị tên cha "Điện tử" ở ĐÚNG dòng của nó, KHÔNG
    // PHẢI id "1" trơ.
    const childRow = table.getByText("Điện thoại").closest("tr");
    expect(childRow).not.toBeNull();
    expect(within(childRow as HTMLElement).getByText("Điện tử")).toBeInTheDocument();
  });

  it("hiện đúng tổng số danh mục ở footer, KHÔNG có dạng X-Y (GET /categories không phân trang thật)", () => {
    render(<CategoryTable {...noopProps} categories={[parentCategory, childCategory]} />);
    expect(screen.getByText("Tổng 2 danh mục")).toBeInTheDocument();
    expect(screen.queryByText(/Hiển thị/)).not.toBeInTheDocument();
  });

  it("danh mục KHÔNG có cha hiển thị '—' ở cột Danh mục cha", () => {
    render(<CategoryTable {...noopProps} categories={[parentCategory]} />);
    const row = screen.getByText("Điện tử").closest("tr") as HTMLElement;
    expect(within(row).getByText("—")).toBeInTheDocument();
  });

  it("bấm Xóa nhưng KHÔNG xác nhận confirm() -> KHÔNG gọi API", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<CategoryTable {...noopProps} categories={[parentCategory]} />);

    await user.click(screen.getByTitle("Xóa"));

    expect(window.confirm).toHaveBeenCalled();
    expect(mockDelete).not.toHaveBeenCalled();
  });

  it("xóa thành công - gọi đúng DELETE /categories/{id}, gọi onChanged", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDelete.mockResolvedValue({ data: { success: true, message: "Đã xóa danh mục" } });
    const onChanged = vi.fn();
    render(<CategoryTable {...noopProps} categories={[parentCategory]} onChanged={onChanged} />);

    await user.click(screen.getByTitle("Xóa"));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("/categories/1"));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("xóa thất bại 409 (còn sản phẩm) - hiện ĐÚNG message thật từ Backend, KHÔNG PHẢI lỗi generic", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDelete.mockRejectedValue(makeApiError(409, "Không thể xóa danh mục còn 20 sản phẩm"));
    render(<CategoryTable {...noopProps} categories={[parentCategory]} />);

    await user.click(screen.getByTitle("Xóa"));

    await waitFor(() => expect(mockToastError).toHaveBeenCalledWith("Không thể xóa danh mục còn 20 sản phẩm"));
  });

  it("xóa thất bại 409 (còn danh mục con) - hiện đúng message thật", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDelete.mockRejectedValue(makeApiError(409, "Không thể xóa danh mục còn 1 danh mục con"));
    render(<CategoryTable {...noopProps} categories={[parentCategory]} />);

    await user.click(screen.getByTitle("Xóa"));

    await waitFor(() => expect(mockToastError).toHaveBeenCalledWith("Không thể xóa danh mục còn 1 danh mục con"));
  });

  it("bấm Sửa gọi onEdit với đúng category", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(<CategoryTable {...noopProps} categories={[parentCategory]} onEdit={onEdit} />);

    await user.click(screen.getByTitle("Sửa"));

    expect(onEdit).toHaveBeenCalledWith(parentCategory);
  });
});
