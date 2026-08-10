import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductFormModal } from "@/components/admin/ProductFormModal";
import type { Category } from "@/types/category";
import type { Product } from "@/types/product";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
  },
}));

const categories: Category[] = [
  { id: 1, name: "Gốm sứ", description: null },
  { id: 2, name: "Vải dệt", description: null },
];

const existingProduct: Product = {
  id: 5,
  category: { id: 2, name: "Vải dệt" },
  name: "Khăn lanh",
  slug: "khan-lanh",
  description: "Mô tả cũ",
  price: "200000",
  stock_quantity: 12,
  image_url: null,
  is_active: true,
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

describe("ProductFormModal (task 4.4.1)", () => {
  beforeEach(() => {
    mockPost.mockResolvedValue({
      data: {
        success: true,
        message: "Tạo sản phẩm thành công",
        data: { ...existingProduct, id: 99, name: "Sản phẩm mới" },
      },
    });
    mockPut.mockResolvedValue({ data: { success: true, message: "", data: existingProduct } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("hiện lỗi validate khi bỏ trống tên/danh mục/giá rồi submit", async () => {
    const user = userEvent.setup();
    render(
      <ProductFormModal isOpen onClose={vi.fn()} product={null} categories={categories} onSaved={vi.fn()} />,
    );

    await user.click(screen.getByRole("button", { name: "Lưu sản phẩm" }));

    expect(await screen.findByText("Vui lòng nhập tên sản phẩm.")).toBeInTheDocument();
    expect(screen.getByText("Vui lòng chọn danh mục.")).toBeInTheDocument();
    expect(screen.getByText("Vui lòng nhập giá.")).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("chế độ TẠO MỚI - submit hợp lệ gọi đúng POST /products, không gọi PUT", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const onClose = vi.fn();
    render(
      <ProductFormModal isOpen onClose={onClose} product={null} categories={categories} onSaved={onSaved} />,
    );

    await user.type(screen.getByLabelText("Tên sản phẩm *"), "Bình gốm mới");
    await user.selectOptions(screen.getByLabelText("Danh mục"), "1");
    await user.type(screen.getByLabelText("Giá (₫) *"), "150000");

    await user.click(screen.getByRole("button", { name: "Lưu sản phẩm" }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith("/products", {
        name: "Bình gốm mới",
        category_id: 1,
        price: "150000",
        description: undefined,
      }),
    );
    expect(mockPut).not.toHaveBeenCalled();
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(onClose).toHaveBeenCalled();
  });

  it("chế độ SỬA - pre-fill đúng giá trị hiện tại, submit gọi đúng PUT /products/{id}", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    render(
      <ProductFormModal
        isOpen
        onClose={vi.fn()}
        product={existingProduct}
        categories={categories}
        onSaved={onSaved}
      />,
    );

    expect(await screen.findByDisplayValue("Khăn lanh")).toBeInTheDocument();
    expect(screen.getByDisplayValue("200000")).toBeInTheDocument();

    const priceInput = screen.getByLabelText("Giá (₫) *");
    await user.clear(priceInput);
    await user.type(priceInput, "220000");

    await user.click(screen.getByRole("button", { name: "Lưu sản phẩm" }));

    await waitFor(() =>
      expect(mockPut).toHaveBeenCalledWith("/products/5", {
        name: "Khăn lanh",
        category_id: 2,
        price: "220000",
        description: "Mô tả cũ",
        is_active: true,
      }),
    );
    expect(mockPost).not.toHaveBeenCalled();
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });
});
