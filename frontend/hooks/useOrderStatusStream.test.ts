import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useOrderStatusStream } from "@/hooks/useOrderStatusStream";

// task 5.2.2 - test vòng đời kết nối SSE (không cần browser/backend thật,
// cùng tinh thần useChatSocket.test.ts) - tự mock EventSource toàn cục +
// lib/auth. KHÁC useChatSocket.test.ts ở điểm cốt lõi: KHÔNG test backoff
// timer tự viết tay (không có, EventSource tự quản lý retry built-in) - chỉ
// test hook phản ánh đúng readyState + tự đóng khi token hết hạn.

let tokenExpired = false;
vi.mock("@/lib/auth", () => ({
  getToken: () => "fake-token",
  isTokenExpired: () => tokenExpired,
}));

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  readyState = FakeEventSource.CONNECTING;
  onerror: (() => void) | null = null;
  private listeners: Record<string, ((event: MessageEvent<string>) => void)[]> = {};

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, cb: (event: MessageEvent<string>) => void) {
    (this.listeners[type] ??= []).push(cb);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }

  /** Test helper - giả lập server gửi event "connected" thật. */
  simulateConnected() {
    this.readyState = FakeEventSource.OPEN;
    this.listeners["connected"]?.forEach((cb) => cb(new MessageEvent("connected", { data: JSON.stringify({ user_id: 1 }) })));
  }

  /** Test helper - giả lập server gửi event "order_status" thật. */
  simulateOrderStatus(payload: unknown) {
    this.listeners["order_status"]?.forEach((cb) =>
      cb(new MessageEvent("order_status", { data: JSON.stringify(payload) })),
    );
  }

  /** Test helper - giả lập payload "order_status" sai định dạng JSON (lỗi hạ tầng giả định). */
  simulateRawOrderStatus(rawData: string) {
    this.listeners["order_status"]?.forEach((cb) => cb(new MessageEvent("order_status", { data: rawData })));
  }

  /** Test helper - giả lập lỗi hạ tầng (mạng/server ngắt) - readyState do trình
   * duyệt THẬT tự quyết định (CONNECTING nếu đang tự retry, CLOSED nếu bỏ cuộc hẳn). */
  simulateError(readyState: number) {
    this.readyState = readyState;
    this.onerror?.();
  }
}

function latestSource(): FakeEventSource {
  const es = FakeEventSource.instances[FakeEventSource.instances.length - 1];
  if (!es) throw new Error("Chưa có EventSource instance nào được tạo");
  return es;
}

describe("useOrderStatusStream (task 5.2.2)", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    tokenExpired = false;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mở đúng 1 kết nối khi enabled=true, gắn token vào query string", () => {
    renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(latestSource().url).toContain("/notifications/orders/stream?token=fake-token");
  });

  it("KHÔNG mở kết nối nào khi enabled=false", () => {
    renderHook(() => useOrderStatusStream({ enabled: false, onOrderStatus: vi.fn() }));
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("chuyển status 'open' khi nhận event 'connected'", () => {
    const { result } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));

    act(() => {
      latestSource().simulateConnected();
    });
    expect(result.current.status).toBe("open");
  });

  it("gọi onOrderStatus với đúng payload đã parse khi nhận event 'order_status'", () => {
    const onOrderStatus = vi.fn();
    renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus }));

    act(() => {
      latestSource().simulateConnected();
      latestSource().simulateOrderStatus({ order_id: 42, status: "confirmed", timestamp: "2026-08-30T00:00:00Z" });
    });

    expect(onOrderStatus).toHaveBeenCalledWith({ order_id: 42, status: "confirmed", timestamp: "2026-08-30T00:00:00Z" });
  });

  it("readyState CONNECTING lúc onerror -> 'reconnecting' (tin tưởng EventSource tự retry, KHÔNG tự tạo connection mới)", () => {
    const { result } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));

    act(() => {
      latestSource().simulateConnected();
      latestSource().simulateError(FakeEventSource.CONNECTING);
    });

    expect(result.current.status).toBe("reconnecting");
    // KHÔNG tự tạo thêm EventSource - hoàn toàn để trình duyệt tự lo (test
    // này tồn tại để bắt lỗi nếu sau này ai lỡ thêm 1 lớp backoff tay đè lên).
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it("readyState CLOSED lúc onerror (trình duyệt bỏ cuộc hẳn) -> 'retry-exhausted'", () => {
    const { result } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));

    act(() => {
      latestSource().simulateError(FakeEventSource.CLOSED);
    });

    expect(result.current.status).toBe("retry-exhausted");
  });

  it("token hết hạn lúc onerror -> tự close() ngay, chặn đứng vòng lặp retry vô hạn (KNOWN_TODOS #28)", () => {
    const { result } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));
    const es = latestSource();

    tokenExpired = true;
    act(() => {
      // Trình duyệt THẬT vẫn báo readyState=CONNECTING (đang tự retry với
      // token đã chết) - hook phải tự nhận ra qua isTokenExpired(), không
      // dựa vào readyState cho case này.
      es.simulateError(FakeEventSource.CONNECTING);
    });

    expect(es.readyState).toBe(FakeEventSource.CLOSED);
    expect(result.current.status).toBe("retry-exhausted");
  });

  it("retryNow() mở lại kết nối mới ngay lập tức", () => {
    const { result } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));

    act(() => {
      latestSource().simulateError(FakeEventSource.CLOSED);
    });
    expect(result.current.status).toBe("retry-exhausted");

    act(() => {
      result.current.retryNow();
    });
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(result.current.status).not.toBe("retry-exhausted");
  });

  it("unmount đóng kết nối, KHÔNG tạo thêm connection sau đó", () => {
    const { unmount } = renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus: vi.fn() }));
    const es = latestSource();

    unmount();

    expect(es.readyState).toBe(FakeEventSource.CLOSED);
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it("enabled chuyển false -> đóng kết nối có chủ đích, KHÔNG coi là mất kết nối", () => {
    const { result, rerender } = renderHook(({ enabled }) => useOrderStatusStream({ enabled, onOrderStatus: vi.fn() }), {
      initialProps: { enabled: true },
    });

    act(() => {
      latestSource().simulateConnected();
    });
    expect(result.current.status).toBe("open");

    rerender({ enabled: false });
    expect(latestSource().readyState).toBe(FakeEventSource.CLOSED);
  });

  it("payload 'order_status' sai định dạng JSON - bỏ qua, không throw, không gọi callback", () => {
    const onOrderStatus = vi.fn();
    renderHook(() => useOrderStatusStream({ enabled: true, onOrderStatus }));

    expect(() => {
      act(() => {
        latestSource().simulateRawOrderStatus("{ dữ liệu không phải JSON hợp lệ");
      });
    }).not.toThrow();
    expect(onOrderStatus).not.toHaveBeenCalled();
  });
});
