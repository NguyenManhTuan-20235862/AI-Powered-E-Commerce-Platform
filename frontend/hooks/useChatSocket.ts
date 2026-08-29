"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getToken, isTokenExpired } from "@/lib/auth";
import type { ChatConnectionStatus, ChatMessageItem, ChatServerEvent } from "@/types/chat";

// Backoff tăng dần theo công thức (task 5.1.2) - 1s, 2s, 4s, 8s, 16s, cap ở
// 30s cho nấc xa hơn (dù thực tế KHÔNG bao giờ tới nấc thứ 6 vì dừng hẳn sau
// MAX_AUTO_RETRIES lần - vẫn viết đúng công thức có cap thay vì mảng cứng 5
// phần tử, để "không retry vô hạn dồn dập" đúng cả về mặt công thức lẫn hành
// vi). Reset retryCount về 0 ngay khi có 1 lần connect thành công (nhận được
// event "connected").
export const RECONNECT_BASE_DELAY_MS = 1000;
export const RECONNECT_MAX_DELAY_MS = 30000;
export const MAX_AUTO_RETRIES = 5;

export function getReconnectDelayMs(retryIndex: number): number {
  return Math.min(RECONNECT_BASE_DELAY_MS * 2 ** retryIndex, RECONNECT_MAX_DELAY_MS);
}

function buildWebSocketUrl(token: string): string {
  // NEXT_PUBLIC_API_URL (VD http://localhost:8000/api/v1) - đổi scheme
  // http/https -> ws/wss, GIỮ NGUYÊN phần còn lại (đã có sẵn "/api/v1", path
  // thật là /api/v1/ws/chat, không phải /ws/chat trơn - xem CLAUDE.md).
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/ws/chat?token=${encodeURIComponent(token)}`;
}

function randomId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Quản lý vòng đời kết nối WebSocket /ws/chat (task 5.1.2) - hook cục bộ
 * (KHÔNG phải Context, xác nhận đã chốt): chỉ `ChatWidget.tsx` dùng, không
 * component nào khác trong dự án cần đọc state này, khác hẳn lý do
 * `CartContext` cần Context (nhiều component rải rác cùng cần đọc).
 *
 * `enabled` do `ChatWidget` điều khiển theo trạng thái mở/đóng panel - CHỈ
 * mở kết nối thật khi panel đang mở (tiết kiệm tài nguyên, đúng đề xuất task
 * 5.1.2), đóng sạch khi panel đóng/component unmount.
 *
 * Trình duyệt KHÔNG đọc được close code 4001/4003 (luôn thấy 1006 chung
 * chung - xem KNOWN_TODOS #2, CLAUDE.md) - tự kiểm tra token hết hạn qua
 * `isTokenExpired()` TRƯỚC khi mở kết nối để bắt sớm case phổ biến nhất,
 * nhưng vẫn phải coi MỌI lần đóng kết nối (dù lý do gì) là "mất kết nối"
 * chung, không cố phân biệt nguyên nhân qua code.
 */
export function useChatSocket({ enabled, onServerError }: { enabled: boolean; onServerError?: (message: string) => void }) {
  const [status, setStatus] = useState<ChatConnectionStatus>("idle");
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  // Ref thay vì đưa thẳng onServerError vào deps của connect() - ChatWidget
  // truyền callback này có thể đổi identity mỗi render (không memo hoá), đưa
  // trực tiếp vào deps sẽ khiến connect() (và effect kết nối bên dưới) đổi
  // theo mỗi render, mất tính ổn định đang cố giữ.
  const onServerErrorRef = useRef(onServerError);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Cờ để phân biệt "đóng có chủ đích" (disconnect()/unmount) với "mất kết
  // nối ngoài ý muốn" trong onclose - chỉ retry ở trường hợp sau.
  const intentionalCloseRef = useRef(false);

  useEffect(() => {
    onServerErrorRef.current = onServerError;
  }, [onServerError]);

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      setStatus("retry-exhausted");
      return;
    }

    intentionalCloseRef.current = false;
    setStatus((current) => (current === "idle" ? "connecting" : current));

    const ws = new WebSocket(buildWebSocketUrl(token));
    wsRef.current = ws;

    ws.onopen = () => {
      // Chưa coi là "open" ở đây - đợi đúng event "connected" từ server (xác
      // nhận handshake auth đã qua, không chỉ TCP/HTTP upgrade đã xong).
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      let data: ChatServerEvent;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === "connected") {
        retryCountRef.current = 0;
        setStatus("open");
        return;
      }

      if (data.type === "reply") {
        setMessages((prev) => [...prev, { id: randomId(), role: data.role, message: data.message }]);
        return;
      }

      // "error" (task 5.1.1 - tin nhắn sai schema/lỗi hạ tầng lúc lưu) - lỗi
      // TẠM THỜI cho 1 tin nhắn cụ thể, KHÔNG đại diện cho việc mất kết nối,
      // không đưa vào danh sách message (giữ message list chỉ chứa hội thoại
      // thật) - hiện qua toast riêng, xem ChatWidget.tsx.
      onServerErrorRef.current?.(data.message);
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (intentionalCloseRef.current) {
        setStatus("idle");
        return;
      }

      if (retryCountRef.current >= MAX_AUTO_RETRIES) {
        setStatus("retry-exhausted");
        return;
      }

      setStatus("reconnecting");
      const delay = getReconnectDelayMs(retryCountRef.current);
      retryCountRef.current += 1;
      clearRetryTimer();
      retryTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = () => {
      // onclose luôn được gọi ngay sau onerror (đúng theo spec WebSocket) -
      // xử lý reconnect tập trung ở onclose, tránh trùng lặp logic ở đây.
    };
  }, [clearRetryTimer]);

  const retryNow = useCallback(() => {
    clearRetryTimer();
    retryCountRef.current = 0;
    setStatus("connecting");
    connect();
  }, [clearRetryTimer, connect]);

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed || wsRef.current?.readyState !== WebSocket.OPEN) return;

    // Optimistic (task 5.1.2) - hiện NGAY tin nhắn user, không đợi phản hồi -
    // Backend là nguồn sự thật cho việc LƯU (chat_logs), không phải cho việc
    // HIỂN THỊ tin nhắn user vừa gửi (khác nguyên tắc CartContext - ở đây
    // không có khái niệm "Backend từ chối 1 phần" cho 1 tin nhắn chat).
    setMessages((prev) => [...prev, { id: randomId(), role: "user", message: trimmed }]);
    wsRef.current.send(JSON.stringify({ message: trimmed }));
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      intentionalCloseRef.current = true;
      clearRetryTimer();
      wsRef.current?.close(1000, "Đóng panel");
      wsRef.current = null;
    };
  }, [enabled, connect, clearRetryTimer]);

  return { status, messages, sendMessage, retryNow };
}
