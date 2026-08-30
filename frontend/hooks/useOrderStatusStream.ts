"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getToken, isTokenExpired } from "@/lib/auth";
import type { OrderStatusEvent, OrderStreamStatus } from "@/types/notification";

function buildStreamUrl(token: string): string {
  // NEXT_PUBLIC_API_URL (VD http://localhost:8000/api/v1) - path thật
  // /api/v1/notifications/orders/stream, xem CLAUDE.md.
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  return `${base}/notifications/orders/stream?token=${encodeURIComponent(token)}`;
}

/**
 * Quản lý kết nối SSE `/notifications/orders/stream` (task 5.2.2) - CHỈ mở
 * khi `enabled=true` (page-scoped, xác nhận trước khi code: chỉ trang
 * `/orders` cần, KHÔNG mở toàn cục ở layout - tránh giữ subscribe Redis
 * không cần thiết cho mọi trang Customer).
 *
 * KHÁC `useChatSocket.ts` (WebSocket, task 5.1.2) ở điểm cốt lõi: `EventSource`
 * TỰ ĐỘNG reconnect sau lỗi theo chu kỳ built-in của trình duyệt - hook này
 * KHÔNG tự viết lại exponential backoff/retryCount đè lên cơ chế đó (xác nhận
 * trước khi code). Rủi ro DUY NHẤT cần tự chặn (KNOWN_TODOS #28): access
 * token hết hạn (60 phút) trong lúc tab vẫn mở - trình duyệt KHÔNG tự phân
 * biệt được 401 (token chết) với lỗi mạng tạm thời, sẽ cứ retry với token đã
 * chết ĐỀU ĐẶN VÔ THỜI HẠN nếu không tự đóng - nên mỗi lần `onerror` bắn, tự
 * kiểm tra `isTokenExpired()` (cùng hàm `useChatSocket.ts` dùng), hết hạn thì
 * tự `close()` để chặn đứng vòng lặp, chuyển "retry-exhausted" (cần
 * `retryNow()` thủ công - thực tế là đăng nhập lại trước, xem OrdersView.tsx).
 */
export function useOrderStatusStream({
  enabled,
  onOrderStatus,
}: {
  enabled: boolean;
  onOrderStatus: (event: OrderStatusEvent) => void;
}) {
  const [status, setStatus] = useState<OrderStreamStatus>("idle");

  const esRef = useRef<EventSource | null>(null);
  // Ref thay vì đưa thẳng onOrderStatus vào deps của connect() - OrdersView
  // truyền callback có thể đổi identity mỗi render, cùng lý do
  // onServerErrorRef ở useChatSocket.ts.
  const onOrderStatusRef = useRef(onOrderStatus);
  const intentionalCloseRef = useRef(false);

  useEffect(() => {
    onOrderStatusRef.current = onOrderStatus;
  }, [onOrderStatus]);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      setStatus("retry-exhausted");
      return;
    }

    intentionalCloseRef.current = false;
    setStatus((current) => (current === "idle" ? "connecting" : current));

    const es = new EventSource(buildStreamUrl(token));
    esRef.current = es;

    es.addEventListener("connected", () => {
      setStatus("open");
    });

    es.addEventListener("order_status", (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as OrderStatusEvent;
        onOrderStatusRef.current(data);
      } catch {
        // Payload không parse được - bỏ qua 1 sự kiện, KHÔNG coi là mất kết
        // nối (khác lỗi hạ tầng thật ở onerror bên dưới).
      }
    });

    es.onerror = () => {
      if (intentionalCloseRef.current) return;

      const currentToken = getToken();
      if (!currentToken || isTokenExpired(currentToken)) {
        es.close();
        esRef.current = null;
        setStatus("retry-exhausted");
        return;
      }

      // readyState === CLOSED: trình duyệt đã bỏ cuộc hẳn (không tự retry
      // nữa - cần retryNow() thủ công). readyState === CONNECTING: trình
      // duyệt đang tự thử lại built-in - chỉ phản ánh trạng thái, không tự
      // làm gì thêm (không tạo EventSource mới, không hẹn giờ tay).
      setStatus(es.readyState === EventSource.CLOSED ? "retry-exhausted" : "reconnecting");
    };
  }, []);

  const retryNow = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setStatus("connecting");
    connect();
  }, [connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      intentionalCloseRef.current = true;
      esRef.current?.close();
      esRef.current = null;
    };
  }, [enabled, connect]);

  return { status, retryNow };
}
