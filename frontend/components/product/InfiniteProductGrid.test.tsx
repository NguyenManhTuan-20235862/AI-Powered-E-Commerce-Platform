import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InfiniteProductGrid } from "@/components/product/InfiniteProductGrid";
import type { Product } from "@/types/product";

// task 4.5.2 - test LOGIC tải thêm (gọi API đúng trang, nối danh sách, dừng
// đúng lúc, không gọi trùng) - không cần browser thật cho phần này (khác UX
// cuộn mượt, verify riêng bằng browser thật). jsdom KHÔNG có IntersectionObserver
// - tự mock 1 bản tối giản, lưu lại callback để test tự "bắn" sự kiện giao
// nhau thay vì cuộn thật.
// Mỗi instance tự theo dõi trạng thái "đã disconnect" riêng (khớp đúng hành
// vi trình duyệt thật: gọi disconnect() rồi thì callback KHÔNG BAO GIỜ được
// gọi lại nữa, kể cả khi có sự kiện giao nhau mới) - dùng mảng thay vì 1
// biến callback đơn lẻ để bắt đúng bug thật nếu component quên disconnect
// observer cũ trước khi tạo observer mới.
let observerInstances: { callback: IntersectionObserverCallback; disconnected: boolean }[] = [];
const observeMock = vi.fn();
const disconnectMock = vi.fn();

class FakeIntersectionObserver {
  private entry: { callback: IntersectionObserverCallback; disconnected: boolean };
  constructor(callback: IntersectionObserverCallback) {
    this.entry = { callback, disconnected: false };
    observerInstances.push(this.entry);
  }
  observe = observeMock;
  disconnect = () => {
    this.entry.disconnected = true;
    disconnectMock();
  };
  unobserve = vi.fn();
}

// `act()` vì callback bắn `setIsLoadingMore(true)` NGAY (đồng bộ) trước khi
// `await` request - RTL không tự biết bọc hộ vì lời gọi này không đi qua
// `fireEvent`/user-event (IntersectionObserver không phải sự kiện DOM).
function fireIntersection(isIntersecting = true) {
  const active = observerInstances[observerInstances.length - 1];
  if (!active || active.disconnected) return;
  act(() => {
    active.callback([{ isIntersecting } as IntersectionObserverEntry], null as unknown as IntersectionObserver);
  });
}

const apiGetMock = vi.fn();
vi.mock("@/lib/axios", () => ({
  api: { get: (...args: unknown[]) => apiGetMock(...args) },
}));

// ProductCardClient -> AddToCartButton cần useRouter() + useCart() - mock cả
// 2 ở boundary, không cần dựng nguyên CartProvider/AuthProvider cho test này
// (đúng phạm vi task: test logic tải thêm, không phải luồng giỏ hàng).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/context/CartContext", () => ({
  useCart: () => ({ addItem: vi.fn(), isAuthenticated: false }),
  cartErrorMessage: () => "Lỗi",
}));

function makeProduct(id: number): Product {
  return {
    id,
    category: { id: 1, name: "Gốm sứ" },
    name: `Sản phẩm ${id}`,
    slug: `san-pham-${id}`,
    description: null,
    price: "100000.00",
    stock_quantity: 10,
    image_url: null,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("InfiniteProductGrid - logic tải thêm (task 4.5.2)", () => {
  beforeEach(() => {
    vi.stubGlobal("IntersectionObserver", FakeIntersectionObserver);
    observerInstances = [];
    observeMock.mockClear();
    disconnectMock.mockClear();
    apiGetMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hiển thị đúng sản phẩm trang 1 (SSR) và quan sát sentinel khi còn trang sau", () => {
    render(
      <InfiniteProductGrid
        initialProducts={[makeProduct(1), makeProduct(2)]}
        initialTotal={5}
        initialTotalPages={3}
        queryParams={{}}
      />,
    );

    expect(screen.getByText("Sản phẩm 1")).toBeInTheDocument();
    expect(screen.getByText("Sản phẩm 2")).toBeInTheDocument();
    expect(observeMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/Đã hiển thị tất cả/)).not.toBeInTheDocument();
  });

  it("gọi đúng trang kế tiếp + nối thêm sản phẩm khi sentinel giao nhau viewport", async () => {
    apiGetMock.mockResolvedValueOnce({
      data: { data: { items: [makeProduct(3), makeProduct(4)], total: 5, page: 2, page_size: 2, total_pages: 3 } },
    });

    render(
      <InfiniteProductGrid
        initialProducts={[makeProduct(1), makeProduct(2)]}
        initialTotal={5}
        initialTotalPages={3}
        queryParams={{ category_id: "1", sort_by: "price_asc" }}
      />,
    );

    fireIntersection();

    await waitFor(() => expect(screen.getByText("Sản phẩm 3")).toBeInTheDocument());
    expect(screen.getByText("Sản phẩm 4")).toBeInTheDocument();
    // Sản phẩm trang 1 vẫn còn - nối thêm, không thay thế.
    expect(screen.getByText("Sản phẩm 1")).toBeInTheDocument();

    expect(apiGetMock).toHaveBeenCalledWith(
      "/products",
      expect.objectContaining({
        params: { category_id: "1", sort_by: "price_asc", page: 2, page_size: 12 },
      }),
    );
  });

  it("không gọi trùng API nếu sentinel bắn nhiều lần liên tiếp trước khi request trước hoàn tất", async () => {
    let resolveFirst!: (v: unknown) => void;
    apiGetMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    );

    render(
      <InfiniteProductGrid
        initialProducts={[makeProduct(1)]}
        initialTotal={3}
        initialTotalPages={3}
        queryParams={{}}
      />,
    );

    fireIntersection();
    fireIntersection();
    fireIntersection();

    expect(apiGetMock).toHaveBeenCalledTimes(1);

    resolveFirst({ data: { data: { items: [makeProduct(2)], total: 3, page: 2, page_size: 1, total_pages: 3 } } });
    await waitFor(() => expect(screen.getByText("Sản phẩm 2")).toBeInTheDocument());
  });

  it("dừng quan sát + hiện thông báo đã tải hết khi hết trang, không gọi thêm API", async () => {
    apiGetMock.mockResolvedValueOnce({
      data: { data: { items: [makeProduct(2)], total: 2, page: 2, page_size: 1, total_pages: 2 } },
    });

    render(
      <InfiniteProductGrid
        initialProducts={[makeProduct(1)]}
        initialTotal={2}
        initialTotalPages={2}
        queryParams={{}}
      />,
    );

    fireIntersection();
    await waitFor(() => expect(screen.getByText("Đã hiển thị tất cả 2 sản phẩm")).toBeInTheDocument());

    apiGetMock.mockClear();
    fireIntersection();
    expect(apiGetMock).not.toHaveBeenCalled();
  });

  it("hiện nút thử lại khi tải thêm thất bại, gọi lại đúng trang khi bấm", async () => {
    apiGetMock.mockRejectedValueOnce(new Error("network"));
    apiGetMock.mockResolvedValueOnce({
      data: { data: { items: [makeProduct(2)], total: 2, page: 2, page_size: 1, total_pages: 2 } },
    });

    render(
      <InfiniteProductGrid
        initialProducts={[makeProduct(1)]}
        initialTotal={2}
        initialTotalPages={2}
        queryParams={{}}
      />,
    );

    fireIntersection();
    const retryButton = await screen.findByRole("button", { name: /Thử lại/ });

    fireEvent.click(retryButton);
    await waitFor(() => expect(screen.getByText("Sản phẩm 2")).toBeInTheDocument());
    expect(apiGetMock).toHaveBeenCalledTimes(2);
  });
});
