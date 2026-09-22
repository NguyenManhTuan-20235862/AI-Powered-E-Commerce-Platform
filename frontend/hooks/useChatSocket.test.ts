import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  MAX_AUTO_RETRIES,
  RECONNECT_MAX_DELAY_MS,
  getReconnectDelayMs,
  useChatSocket,
} from "@/hooks/useChatSocket";

// task 5.1.2 - test logic backoff/reconnect của useChatSocket.ts (không cần
// browser/backend thật cho phần này) - tự mock WebSocket toàn cục + lib/auth,
// dùng fake timer để kiểm tra CHÍNH XÁC thời điểm mỗi lần thử kết nối lại.

vi.mock("@/lib/auth", () => ({
  getToken: () => "fake-token",
  isTokenExpired: () => false,
}));

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readyState = FakeWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
  }

  /** Test helper - giả lập server chấp nhận + gửi event "connected" thật. */
  simulateConnected(sessionId = "sess-1") {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify({ type: "connected", session_id: sessionId }) }));
  }

  /** Test helper - giả lập mất kết nối ngoài ý muốn (KHÔNG qua disconnect() có chủ đích). */
  simulateUnexpectedClose() {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }

  /** Test helper (task 6.1.2) - giả lập server gửi 1 event JSON bất kỳ. */
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
  }
}

function latestSocket(): FakeWebSocket {
  const ws = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  if (!ws) throw new Error("Chưa có WebSocket instance nào được tạo");
  return ws;
}

describe("getReconnectDelayMs - công thức backoff (task 5.1.2)", () => {
  it("tăng gấp đôi đúng 1s -> 2s -> 4s -> 8s -> 16s rồi cap ở 30s", () => {
    expect(getReconnectDelayMs(0)).toBe(1000);
    expect(getReconnectDelayMs(1)).toBe(2000);
    expect(getReconnectDelayMs(2)).toBe(4000);
    expect(getReconnectDelayMs(3)).toBe(8000);
    expect(getReconnectDelayMs(4)).toBe(16000);
    // 2^5 * 1000 = 32000 -> vượt cap, phải bị chặn lại đúng 30000.
    expect(getReconnectDelayMs(5)).toBe(RECONNECT_MAX_DELAY_MS);
    expect(getReconnectDelayMs(5)).toBe(30000);
    // Nấc xa hơn nữa vẫn phải GIỮ NGUYÊN ở cap, không tăng tiếp.
    expect(getReconnectDelayMs(9)).toBe(30000);
  });
});

describe("useChatSocket - vòng đời reconnect (task 5.1.2)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("WebSocket", FakeWebSocket);
    FakeWebSocket.instances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("thử lại đúng trình tự backoff 1s->2s->4s->8s->16s, KHÔNG tạo connection mới trước thời điểm đó", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    expect(FakeWebSocket.instances).toHaveLength(1);

    const delays = [1000, 2000, 4000, 8000, 16000];
    for (const delay of delays) {
      const countBefore = FakeWebSocket.instances.length;

      act(() => {
        latestSocket().simulateUnexpectedClose();
      });
      expect(result.current.status).toBe("reconnecting");

      // Ngay trước mốc thời gian - CHƯA được tạo connection mới.
      act(() => {
        vi.advanceTimersByTime(delay - 1);
      });
      expect(FakeWebSocket.instances).toHaveLength(countBefore);

      // Đúng mốc thời gian - PHẢI tạo connection mới (retry kế tiếp).
      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(FakeWebSocket.instances).toHaveLength(countBefore + 1);
    }

    // Đã retry đủ MAX_AUTO_RETRIES (5) lần, khớp đúng danh sách delays ở trên.
    expect(MAX_AUTO_RETRIES).toBe(5);
    expect(FakeWebSocket.instances).toHaveLength(1 + delays.length);
  });

  it("dừng tự động retry sau đúng 5 lần liên tiếp thất bại, hiện trạng thái để bấm Kết nối lại", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));

    // Thất bại lần đầu (connect ban đầu) + đủ 5 lần retry, TẤT CẢ đều thất bại.
    for (let i = 0; i < MAX_AUTO_RETRIES; i++) {
      act(() => {
        latestSocket().simulateUnexpectedClose();
      });
      act(() => {
        vi.advanceTimersByTime(getReconnectDelayMs(i));
      });
    }

    expect(FakeWebSocket.instances).toHaveLength(1 + MAX_AUTO_RETRIES);

    // Lần thất bại thứ 5 (retry cuối) - KHÔNG còn tự động lên lịch retry nữa.
    act(() => {
      latestSocket().simulateUnexpectedClose();
    });
    expect(result.current.status).toBe("retry-exhausted");

    // Dù chờ rất lâu (hơn cả mức cap 30s) cũng KHÔNG tự tạo thêm connection.
    act(() => {
      vi.advanceTimersByTime(RECONNECT_MAX_DELAY_MS * 2);
    });
    expect(FakeWebSocket.instances).toHaveLength(1 + MAX_AUTO_RETRIES);

    // retryNow() (nút "Kết nối lại" thủ công) - kết nối NGAY, không đợi backoff.
    act(() => {
      result.current.retryNow();
    });
    expect(FakeWebSocket.instances).toHaveLength(1 + MAX_AUTO_RETRIES + 1);
    expect(result.current.status).not.toBe("retry-exhausted");
  });

  it("reset backoff về nấc đầu (1s) sau khi có 1 lần connect thành công", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));

    // Retry 2 lần thất bại (1s, 2s) rồi lần thứ 3 THÀNH CÔNG.
    act(() => {
      latestSocket().simulateUnexpectedClose();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      latestSocket().simulateUnexpectedClose();
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      latestSocket().simulateConnected();
    });
    expect(result.current.status).toBe("open");

    // Mất kết nối lại NGAY sau đó - phải bắt đầu LẠI từ 1s, không phải 4s
    // (retryCount đã reset về 0 nhờ lần connect thành công ở trên).
    const countBefore = FakeWebSocket.instances.length;
    act(() => {
      latestSocket().simulateUnexpectedClose();
    });
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(FakeWebSocket.instances).toHaveLength(countBefore);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeWebSocket.instances).toHaveLength(countBefore + 1);
  });

  it("unmount giữa lúc đang chờ backoff - dọn timer đúng, KHÔNG tạo thêm connection chồng chéo sau đó", () => {
    const { unmount } = renderHook(() => useChatSocket({ enabled: true }));
    expect(FakeWebSocket.instances).toHaveLength(1);

    act(() => {
      latestSocket().simulateUnexpectedClose();
    });
    // Đang chờ backoff 1s thì unmount ngay lúc này.
    unmount();

    act(() => {
      vi.advanceTimersByTime(60000);
    });
    // Timer chờ retry PHẢI đã bị clearTimeout trong cleanup - không có
    // connection nào được tạo thêm dù chờ rất lâu sau khi unmount.
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("đóng có chủ đích (enabled chuyển false) KHÔNG kích hoạt auto-retry", () => {
    const { result, rerender } = renderHook(({ enabled }) => useChatSocket({ enabled }), {
      initialProps: { enabled: true },
    });
    expect(FakeWebSocket.instances).toHaveLength(1);

    act(() => {
      latestSocket().simulateConnected();
    });
    expect(result.current.status).toBe("open");

    // Đóng panel (enabled=false) - đây là close() có chủ đích trong cleanup
    // effect, KHÔNG phải mất kết nối ngoài ý muốn.
    rerender({ enabled: false });

    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});

describe("useChatSocket - streaming chunk/done/error (task 6.1.2)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("WebSocket", FakeWebSocket);
    FakeWebSocket.instances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("gửi tin nhắn -> isStreaming=true NGAY LẬP TỨC (khóa input trước khi có phản hồi)", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    act(() => latestSocket().simulateConnected());
    expect(result.current.isStreaming).toBe(false);

    act(() => result.current.sendMessage("Xin chào"));

    expect(result.current.isStreaming).toBe(true);
  });

  it("chunk ĐẦU TIÊN tạo 1 tin nhắn assistant mới, các chunk SAU nối vào ĐÚNG tin đó (không tạo tin mới)", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    act(() => latestSocket().simulateConnected());
    act(() => result.current.sendMessage("Xin chào"));

    act(() => latestSocket().simulateMessage({ type: "chunk", content: "Xin" }));
    expect(result.current.messages).toHaveLength(2); // user + assistant (chunk 1)
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", message: "Xin" });

    act(() => latestSocket().simulateMessage({ type: "chunk", content: " chào" }));
    act(() => latestSocket().simulateMessage({ type: "chunk", content: "!" }));

    // VẪN đúng 2 tin nhắn (không tạo thêm bubble mới cho mỗi chunk) - nội
    // dung đã nối dần thành câu hoàn chỉnh.
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", message: "Xin chào!" });
    // Cùng 1 id xuyên suốt (đúng 1 bubble được CẬP NHẬT, không phải bị thay bằng bubble khác).
    const assistantId = result.current.messages[1].id;
    act(() => latestSocket().simulateMessage({ type: "chunk", content: " Hi" }));
    expect(result.current.messages[1].id).toBe(assistantId);
  });

  it("nhận 'done' -> isStreaming=false (mở khóa lại input)", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    act(() => latestSocket().simulateConnected());
    act(() => result.current.sendMessage("Xin chào"));
    act(() => latestSocket().simulateMessage({ type: "chunk", content: "Xin chào" }));
    expect(result.current.isStreaming).toBe(true);

    act(() => latestSocket().simulateMessage({ type: "done" }));

    expect(result.current.isStreaming).toBe(false);
  });

  it("nhận 'error' TRƯỚC khi có chunk nào (VD timeout token đầu) -> isStreaming=false, KHÔNG tạo tin nhắn assistant nào", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    act(() => latestSocket().simulateConnected());
    act(() => result.current.sendMessage("Xin chào"));
    expect(result.current.isStreaming).toBe(true);

    act(() => latestSocket().simulateMessage({ type: "error", message: "Trợ lý đang bận, vui lòng thử lại sau" }));

    expect(result.current.isStreaming).toBe(false);
    // Chỉ có đúng tin "user" vừa gửi - KHÔNG có bubble assistant rỗng/lỗi nào bị tạo ra.
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("tin nhắn thứ 2 (sau khi lượt 1 đã 'done') tạo bubble assistant MỚI, không nối vào bubble cũ", () => {
    const { result } = renderHook(() => useChatSocket({ enabled: true }));
    act(() => latestSocket().simulateConnected());

    act(() => result.current.sendMessage("Câu hỏi 1"));
    act(() => latestSocket().simulateMessage({ type: "chunk", content: "Trả lời 1" }));
    act(() => latestSocket().simulateMessage({ type: "done" }));

    act(() => result.current.sendMessage("Câu hỏi 2"));
    act(() => latestSocket().simulateMessage({ type: "chunk", content: "Trả lời 2" }));

    expect(result.current.messages).toHaveLength(4); // user1, assistant1, user2, assistant2
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", message: "Trả lời 1" });
    expect(result.current.messages[3]).toMatchObject({ role: "assistant", message: "Trả lời 2" });
    expect(result.current.messages[1].id).not.toBe(result.current.messages[3].id);
  });
});
