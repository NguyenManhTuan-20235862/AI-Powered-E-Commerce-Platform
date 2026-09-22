import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OrdersView } from "@/components/order/OrdersView";
import type { Order } from "@/types/order";

const mockGet = vi.fn();
const pushMock = vi.fn();
const replaceMock = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock("@/lib/axios", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

// `router` là dependency của fetchOrders() (useCallback, cần cho nhánh tự
// lùi trang bên dưới) - Next.js THẬT trả về router THAM CHIẾU ỔN ĐỊNH xuyên
// suốt vòng đời component (không đổi identity mỗi lần render); mock PHẢI trả
// về CÙNG 1 object mỗi lần gọi useRouter() (khai object 1 LẦN ở module scope,
// KHÔNG tạo `{ push, replace }` mới bên trong factory function) - nếu không,
// fetchOrders() sẽ có identity mới mỗi render -> useEffect gọi lại liên tục,
// "ăn" hết queue mockResolvedValueOnce/mockRejectedValueOnce trước khi kịp
// assert (đã tự gặp lỗi test flaky này lúc viết, không phải bug thật ở component).
const routerMock = { push: pushMock, replace: replaceMock };
vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  useSearchParams: () => currentSearchParams,
}));

// useOrderStatusStream (task 5.2.2) đã có test riêng đầy đủ - mock để cô lập
// test OrdersView khỏi vòng đời EventSource, cùng lý do OrderDetailView.test.tsx.
vi.mock("@/hooks/useOrderStatusStream", () => ({
  useOrderStatusStream: () => ({ status: "open", retryNow: vi.fn() }),
}));

const sampleOrder: Order = {
  id: 5,
  user_id: 1,
  status: "pending",
  total_amount: "200000",
  shipping_name: "Nguyễn Văn A",
  shipping_address: "123 Đường ABC",
  shipping_phone: "0912345678",
  note: null,
  items: [{ id: 1, product_id: 1, product_name: "Bình gốm", quantity: 1, price_at_purchase: "200000" }],
  created_at: "2026-08-01T00:00:00",
  updated_at: "2026-08-01T00:00:00",
};

function pageResponse(items: Order[], totalPages: number) {
  return { data: { success: true, message: "", data: { items, total: items.length, page: 1, page_size: 10, total_pages: totalPages } } };
}

describe("OrdersView - thử lại khi tải lỗi, tự lùi trang khi trang hiện tại thành rỗng", () => {
  beforeEach(() => {
    currentSearchParams = new URLSearchParams();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    pushMock.mockReset();
    replaceMock.mockReset();
  });

  it("tải thành công - hiện danh sách đơn hàng", async () => {
    mockGet.mockResolvedValue(pageResponse([sampleOrder], 1));
    render(<OrdersView />);

    expect(await screen.findByText("Bình gốm")).toBeInTheDocument();
  });

  it("tải lỗi - hiện thông báo lỗi + nút Thử lại; bấm Thử lại gọi lại API và hiện danh sách", async () => {
    const user = userEvent.setup();
    mockGet.mockRejectedValueOnce(new Error("network down"));
    mockGet.mockResolvedValueOnce(pageResponse([sampleOrder], 1));

    render(<OrdersView />);

    expect(await screen.findByText("Không thể tải danh sách đơn hàng. Vui lòng thử lại.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(await screen.findByText("Bình gốm")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it("đang ở trang 2 nhưng fetch trả về total_pages=1 (VD vừa hủy đơn cuối) - tự điều hướng lùi về trang 1 thay vì hiện nhầm 'chưa có đơn hàng nào' vĩnh viễn", async () => {
    // KHÔNG assert UI sau redirect ở đây - mock next/navigation tĩnh (không
    // mô phỏng lại điều hướng thật đổi `?page=`), nên component vẫn tạm hiện
    // "chưa có đơn hàng nào" NGAY SAU khi gọi router.replace() trong 1 lần
    // render (giống hệt hành vi thật: chớp 1 nhịp rồi router điều hướng lại,
    // effect chạy lại với `page` mới) - phần cần xác nhận ở test unit này là
    // ĐÚNG URL đích được tính, không phải toàn bộ vòng điều hướng thật.
    currentSearchParams = new URLSearchParams("page=2");
    mockGet.mockResolvedValue(pageResponse([], 1));

    render(<OrdersView />);

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/orders?page=1"));
    expect(replaceMock).toHaveBeenCalledTimes(1);
  });
});
