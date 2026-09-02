import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProductPagination, getPaginationItems } from "@/components/product/ProductPagination";

describe("getPaginationItems (logic rút gọn '...')", () => {
  it("3 trang - hiện đủ, KHÔNG cần ellipsis dù trang hiện tại ở đâu", () => {
    expect(getPaginationItems(1, 3)).toEqual([1, 2, 3]);
    expect(getPaginationItems(2, 3)).toEqual([1, 2, 3]);
    expect(getPaginationItems(3, 3)).toEqual([1, 2, 3]);
  });

  it("2 trang (VD lọc 'Điện tử' 20 sản phẩm) - hiện đủ, không ellipsis", () => {
    expect(getPaginationItems(1, 2)).toEqual([1, 2]);
    expect(getPaginationItems(2, 2)).toEqual([1, 2]);
  });

  it("chỉ CÁCH nhau đúng 1 trang - điền thẳng số đó, KHÔNG dùng '...' (ẩn không tiết kiệm được gì)", () => {
    // total=8, current=4 -> mustShow neo {1,8} + lân cận {2,3,4,5,6} -> chỉ
    // thiếu đúng trang 7 giữa 6 và 8 -> điền thẳng 7, không phải "...".
    expect(getPaginationItems(4, 8)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });

  it("11 trang (VD 'Tất cả sản phẩm' 123 sản phẩm), trang 1 - ellipsis đúng vị trí", () => {
    // neo {1,11} + lân cận current=1: {1,2,3} (âm bị loại) -> [1,2,3,'...',11]
    expect(getPaginationItems(1, 11)).toEqual([1, 2, 3, "ellipsis", 11]);
  });

  it("11 trang, trang giữa (6) - ellipsis CẢ 2 phía", () => {
    // neo {1,11} + lân cận {4,5,6,7,8} -> [1,'...',4,5,6,7,8,'...',11]
    expect(getPaginationItems(6, 11)).toEqual([1, "ellipsis", 4, 5, 6, 7, 8, "ellipsis", 11]);
  });

  it("11 trang, trang cuối (11) - ellipsis chỉ phía đầu", () => {
    expect(getPaginationItems(11, 11)).toEqual([1, "ellipsis", 9, 10, 11]);
  });

  it("totalPages = 0 -> danh sách rỗng", () => {
    expect(getPaginationItems(1, 0)).toEqual([]);
  });
});

describe("ProductPagination (component)", () => {
  it("totalPages <= 1 -> KHÔNG render gì (không có gì để phân trang)", () => {
    const { container } = render(<ProductPagination currentPage={1} totalPages={1} onPageChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("trang 1 - disabled đúng nút Về trang đầu/Trang trước, KHÔNG disabled Trang sau/Đến trang cuối", () => {
    render(<ProductPagination currentPage={1} totalPages={5} onPageChange={vi.fn()} />);

    expect(screen.getByLabelText("Về trang đầu")).toBeDisabled();
    expect(screen.getByLabelText("Trang trước")).toBeDisabled();
    expect(screen.getByLabelText("Trang sau")).not.toBeDisabled();
    expect(screen.getByLabelText("Đến trang cuối")).not.toBeDisabled();
  });

  it("trang cuối - disabled đúng nút Trang sau/Đến trang cuối, KHÔNG disabled Về trang đầu/Trang trước", () => {
    render(<ProductPagination currentPage={5} totalPages={5} onPageChange={vi.fn()} />);

    expect(screen.getByLabelText("Trang sau")).toBeDisabled();
    expect(screen.getByLabelText("Đến trang cuối")).toBeDisabled();
    expect(screen.getByLabelText("Về trang đầu")).not.toBeDisabled();
    expect(screen.getByLabelText("Trang trước")).not.toBeDisabled();
  });

  it("trang giữa - KHÔNG nút nào bị disabled", () => {
    render(<ProductPagination currentPage={3} totalPages={5} onPageChange={vi.fn()} />);

    expect(screen.getByLabelText("Về trang đầu")).not.toBeDisabled();
    expect(screen.getByLabelText("Trang trước")).not.toBeDisabled();
    expect(screen.getByLabelText("Trang sau")).not.toBeDisabled();
    expect(screen.getByLabelText("Đến trang cuối")).not.toBeDisabled();
  });

  it("nút trang hiện tại có aria-current='page', các nút khác thì không", () => {
    render(<ProductPagination currentPage={3} totalPages={5} onPageChange={vi.fn()} />);

    expect(screen.getByLabelText("Trang 3")).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("Trang 1")).not.toHaveAttribute("aria-current");
  });

  it("bấm số trang gọi đúng onPageChange(số đó)", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<ProductPagination currentPage={1} totalPages={5} onPageChange={onPageChange} />);

    await user.click(screen.getByLabelText("Trang 3"));

    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("bấm '>>' (Đến trang cuối) gọi onPageChange(totalPages)", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<ProductPagination currentPage={1} totalPages={11} onPageChange={onPageChange} />);

    await user.click(screen.getByLabelText("Đến trang cuối"));

    expect(onPageChange).toHaveBeenCalledWith(11);
  });

  it("bấm '<<' (Về trang đầu) gọi onPageChange(1)", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<ProductPagination currentPage={7} totalPages={11} onPageChange={onPageChange} />);

    await user.click(screen.getByLabelText("Về trang đầu"));

    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("bấm '<'/'>' gọi onPageChange(currentPage -+ 1)", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<ProductPagination currentPage={5} totalPages={11} onPageChange={onPageChange} />);

    await user.click(screen.getByLabelText("Trang trước"));
    expect(onPageChange).toHaveBeenCalledWith(4);

    await user.click(screen.getByLabelText("Trang sau"));
    expect(onPageChange).toHaveBeenCalledWith(6);
  });

  it("touch target các nút điều hướng/số trang đủ 40x40px (h-10 w-10)", () => {
    render(<ProductPagination currentPage={1} totalPages={5} onPageChange={vi.fn()} />);

    expect(screen.getByLabelText("Về trang đầu")).toHaveClass("h-10", "w-10");
    expect(screen.getByLabelText("Trang 1")).toHaveClass("h-10", "w-10");
  });
});
