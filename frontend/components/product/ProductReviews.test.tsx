import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProductReviews } from "@/components/product/ProductReviews";
import type { Order } from "@/types/order";
import type { Review, ReviewListResponse } from "@/types/review";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

type MockAuthState = {
  user: { id: number; role: "customer" | "admin" } | null;
  isAuthenticated: boolean;
};
let mockAuthState: MockAuthState = { user: null, isAuthenticated: false };

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockAuthState.user,
    isAuthenticated: mockAuthState.isAuthenticated,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

const PRODUCT_ID = 42;

const sampleReview: Review = {
  id: "abc123",
  product_id: PRODUCT_ID,
  user_id: 10,
  user_name: "Trần Thị B",
  order_id: 100,
  rating: 5,
  comment: "Rất tốt",
  images: null,
  is_verified_purchase: true,
  created_at: "2026-08-01T00:00:00",
  updated_at: null,
};

function reviewsResponse(items: Review[], overrides: Partial<ReviewListResponse> = {}) {
  return {
    data: {
      success: true,
      message: "",
      data: {
        items,
        total: items.length,
        page: 1,
        page_size: 5,
        total_pages: 1,
        average_rating: items.length > 0 ? items[0].rating : null,
        ...overrides,
      },
    },
  };
}

function deliveredOrder(id: number, containsProduct: boolean): Order {
  return {
    id,
    user_id: 10,
    status: "delivered",
    total_amount: "150000",
    shipping_name: "Trần Thị B",
    shipping_address: "123 Đường ABC",
    shipping_phone: "0912345678",
    note: null,
    items: containsProduct
      ? [{ id: 1, product_id: PRODUCT_ID, product_name: "Bình gốm", quantity: 1, price_at_purchase: "150000" }]
      : [{ id: 2, product_id: 999, product_name: "Sản phẩm khác", quantity: 1, price_at_purchase: "50000" }],
    created_at: "2026-07-01T00:00:00",
    updated_at: "2026-07-05T00:00:00",
  };
}

function ordersResponse(items: Order[]) {
  return { data: { success: true, message: "", data: { items, total: items.length, page: 1, page_size: 100, total_pages: 1 } } };
}

function mockRoutes(handlers: { reviews?: unknown; orders?: unknown }) {
  mockGet.mockImplementation((url: string) => {
    if (url === `/products/${PRODUCT_ID}/reviews`) return Promise.resolve(handlers.reviews ?? reviewsResponse([]));
    if (url === "/orders") return Promise.resolve(handlers.orders ?? ordersResponse([]));
    throw new Error(`unexpected GET url: ${url}`);
  });
}

describe("ProductReviews (task Hoàn thiện review sản phẩm)", () => {
  beforeEach(() => {
    mockAuthState = { user: null, isAuthenticated: false };
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPost.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
  });

  it("hiện danh sách review + điểm trung bình + tổng số đánh giá", async () => {
    mockRoutes({ reviews: reviewsResponse([sampleReview], { average_rating: 4.5, total: 3 }) });

    render(<ProductReviews productId={PRODUCT_ID} />);

    expect(await screen.findByText("Trần Thị B")).toBeInTheDocument();
    expect(screen.getByText("Rất tốt")).toBeInTheDocument();
    expect(screen.getByText("4.5")).toBeInTheDocument();
    expect(screen.getByText("3 đánh giá")).toBeInTheDocument();
    expect(screen.getByText("Đã mua hàng")).toBeInTheDocument();
  });

  it("chưa có review nào - hiện thông báo trống, KHÔNG hiện điểm trung bình", async () => {
    mockRoutes({ reviews: reviewsResponse([]) });

    render(<ProductReviews productId={PRODUCT_ID} />);

    expect(await screen.findByText("Chưa có đánh giá nào.")).toBeInTheDocument();
    // Khối tóm tắt điểm trung bình (VD "3 đánh giá") CHỈ hiện khi total > 0.
    expect(screen.queryByText(/^\d+ đánh giá$/)).not.toBeInTheDocument();
  });

  it("lỗi tải review - hiện nút Thử lại, bấm gọi lại API", async () => {
    const user = userEvent.setup();
    mockGet.mockImplementation((url: string) => {
      if (url === `/products/${PRODUCT_ID}/reviews`) return Promise.reject(new Error("network down"));
      return Promise.resolve(ordersResponse([]));
    });

    render(<ProductReviews productId={PRODUCT_ID} />);
    expect(await screen.findByText("Không thể tải đánh giá. Vui lòng thử lại.")).toBeInTheDocument();

    mockGet.mockImplementation((url: string) => {
      if (url === `/products/${PRODUCT_ID}/reviews`) return Promise.resolve(reviewsResponse([sampleReview]));
      return Promise.resolve(ordersResponse([]));
    });
    await user.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(await screen.findByText("Trần Thị B")).toBeInTheDocument();
  });

  it("phân trang - bấm Trang sau gọi lại API với page=2", async () => {
    const user = userEvent.setup();
    mockRoutes({ reviews: reviewsResponse([sampleReview], { total_pages: 2 }) });

    render(<ProductReviews productId={PRODUCT_ID} />);
    await screen.findByText("Trần Thị B");

    await user.click(screen.getByRole("button", { name: "Trang sau" }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith(
        `/products/${PRODUCT_ID}/reviews`,
        expect.objectContaining({ params: { page: 2, page_size: 5 } }),
      ),
    );
  });

  it("chưa đăng nhập - hiện lời mời đăng nhập, KHÔNG hiện form viết đánh giá", async () => {
    mockRoutes({});
    render(<ProductReviews productId={PRODUCT_ID} />);

    expect(await screen.findByText("Chưa có đánh giá nào.")).toBeInTheDocument();
    expect(screen.getByText("Đăng nhập")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Gửi đánh giá" })).not.toBeInTheDocument();
  });

  it("Admin đăng nhập - KHÔNG hiện form viết đánh giá (chỉ Customer)", async () => {
    mockAuthState = { user: { id: 1, role: "admin" }, isAuthenticated: true };
    mockRoutes({});

    render(<ProductReviews productId={PRODUCT_ID} />);
    await screen.findByText("Chưa có đánh giá nào.");

    expect(screen.queryByRole("button", { name: "Gửi đánh giá" })).not.toBeInTheDocument();
  });

  it("Customer đã đăng nhập nhưng CHƯA mua sản phẩm này - hiện thông báo trạng thái 'đã mua hàng'", async () => {
    mockAuthState = { user: { id: 10, role: "customer" }, isAuthenticated: true };
    mockRoutes({ orders: ordersResponse([deliveredOrder(1, false)]) });

    render(<ProductReviews productId={PRODUCT_ID} />);

    expect(
      await screen.findByText("Bạn cần mua và nhận hàng sản phẩm này trước khi có thể đánh giá."),
    ).toBeInTheDocument();
  });

  it("Customer đã mua (delivered) sản phẩm này - hiện form, gửi thành công gọi đúng POST và refetch danh sách", async () => {
    const user = userEvent.setup();
    mockAuthState = { user: { id: 10, role: "customer" }, isAuthenticated: true };
    mockRoutes({ orders: ordersResponse([deliveredOrder(101, true)]) });
    mockPost.mockResolvedValue({ data: { success: true, message: "", data: { ...sampleReview, id: "new-id" } } });

    render(<ProductReviews productId={PRODUCT_ID} />);
    await screen.findByText("Viết đánh giá của bạn");

    await user.click(screen.getByRole("radio", { name: "5 sao" }));
    await user.type(screen.getByLabelText("Nhận xét (không bắt buộc)"), "Tuyệt vời");
    await user.click(screen.getByRole("button", { name: "Gửi đánh giá" }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith(`/products/${PRODUCT_ID}/reviews`, {
        order_id: 101,
        rating: 5,
        comment: "Tuyệt vời",
      }),
    );
    expect(mockToastSuccess).toHaveBeenCalled();
  });

  it("chỉ 1 đơn hợp lệ - KHÔNG hiện dropdown chọn đơn (tự chọn sẵn)", async () => {
    mockAuthState = { user: { id: 10, role: "customer" }, isAuthenticated: true };
    mockRoutes({ orders: ordersResponse([deliveredOrder(101, true)]) });

    render(<ProductReviews productId={PRODUCT_ID} />);
    await screen.findByText("Viết đánh giá của bạn");

    expect(screen.queryByLabelText("Chọn đơn hàng")).not.toBeInTheDocument();
  });

  it("nhiều đơn hợp lệ - HIỆN dropdown chọn đơn", async () => {
    mockAuthState = { user: { id: 10, role: "customer" }, isAuthenticated: true };
    mockRoutes({ orders: ordersResponse([deliveredOrder(101, true), deliveredOrder(102, true)]) });

    render(<ProductReviews productId={PRODUCT_ID} />);
    await screen.findByText("Viết đánh giá của bạn");

    expect(screen.getByLabelText("Chọn đơn hàng")).toBeInTheDocument();
  });
});
