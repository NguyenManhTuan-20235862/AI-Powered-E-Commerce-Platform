import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductFilters } from "@/components/product/ProductFilters";
import type { Category } from "@/types/category";

// Test này bắt LẠI ĐÚNG bug thật đã có từ task 4.2.1 (phát hiện lúc rà soát
// task 4.2.3): ProductFilters lưu category/giá/tồn-kho/search bằng
// `useState(searchParams.get(...))` - initializer đó CHỈ chạy lúc mount.
// Khi URL đổi từ BÊN NGOÀI component (nút back/forward trình duyệt) mà
// KHÔNG qua nút "Áp dụng" ở chính component này, Next.js App Router KHÔNG
// unmount lại ProductFilters - chỉ re-render với `useSearchParams()` trả về
// giá trị mới. Trước khi sửa, widget (checkbox/input) vẫn hiển thị state CŨ
// dù danh sách sản phẩm bên dưới đã đúng theo URL mới - test này giả lập
// đúng kịch bản "không unmount, chỉ đổi hook value" bằng `rerender()`
// (KHÔNG phải render() mới - render() mới sẽ luôn pass dù bug còn tồn tại,
// vì initializer sẽ đọc đúng giá trị mới ngay từ đầu).

let mockSearchParams = new URLSearchParams();
const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => mockSearchParams,
}));

const categories: Category[] = [
  { id: 1, name: "Gốm sứ", description: null },
  { id: 2, name: "Vải dệt", description: null },
];

describe("ProductFilters - đồng bộ URL -> widget (task 4.2.3)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    pushMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("đọc đúng state ban đầu từ URL lúc mount", () => {
    mockSearchParams = new URLSearchParams("category=1");
    render(<ProductFilters categories={categories} />);

    expect((screen.getByLabelText("Gốm sứ") as HTMLInputElement).checked).toBe(true);
    expect((screen.getByLabelText("Vải dệt") as HTMLInputElement).checked).toBe(false);
  });

  it("re-sync checkbox danh mục khi searchParams đổi từ bên ngoài (giả lập back/forward)", () => {
    mockSearchParams = new URLSearchParams("category=1");
    const { rerender } = render(<ProductFilters categories={categories} />);
    expect((screen.getByLabelText("Gốm sứ") as HTMLInputElement).checked).toBe(true);

    // Giả lập back/forward: searchParams đổi TỪ BÊN NGOÀI, component KHÔNG
    // unmount (không gọi lại render() mới) - chỉ rerender với hook mới.
    mockSearchParams = new URLSearchParams("category=2");
    rerender(<ProductFilters categories={categories} />);

    expect((screen.getByLabelText("Gốm sứ") as HTMLInputElement).checked).toBe(false);
    expect((screen.getByLabelText("Vải dệt") as HTMLInputElement).checked).toBe(true);
  });

  it("re-sync ô search và toggle Còn hàng khi searchParams đổi từ bên ngoài", () => {
    mockSearchParams = new URLSearchParams("search=binh+gom&in_stock=1");
    const { rerender } = render(<ProductFilters categories={categories} />);

    expect(screen.getByPlaceholderText("Tên sản phẩm...")).toHaveValue("binh gom");
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");

    mockSearchParams = new URLSearchParams();
    rerender(<ProductFilters categories={categories} />);

    expect(screen.getByPlaceholderText("Tên sản phẩm...")).toHaveValue("");
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  });

  it("re-sync khoảng giá khi searchParams đổi từ bên ngoài", () => {
    mockSearchParams = new URLSearchParams("min_price=100000&max_price=500000");
    const { rerender } = render(<ProductFilters categories={categories} />);

    expect(screen.getByPlaceholderText("Từ")).toHaveValue(100000);
    expect(screen.getByPlaceholderText("Đến")).toHaveValue(500000);

    mockSearchParams = new URLSearchParams();
    rerender(<ProductFilters categories={categories} />);

    expect(screen.getByPlaceholderText("Từ")).toHaveValue(null);
    expect(screen.getByPlaceholderText("Đến")).toHaveValue(null);
  });
});
