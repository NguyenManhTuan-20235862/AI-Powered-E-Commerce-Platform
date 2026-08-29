"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { useAuth } from "@/hooks/useAuth";
import { useChatSocket } from "@/hooks/useChatSocket";

/**
 * Widget chat AI (task 5.1.2) - nút nổi (FAB) + panel, port từ "Collapsed
 * Widget (Desktop)" + "Expanded Panel (Desktop)" + "Vun - Full Screen Chat
 * (Mobile)". Đặt trong `app/(customer)/layout.tsx` (ngang cấp Header/Footer/
 * CartProvider) - CHỈ hiện khi đã đăng nhập (đúng vì `/ws/chat` yêu cầu
 * Customer token, tương tự `CartProvider` chỉ gọi `GET /cart` khi
 * `isAuthenticated`) - ẩn hẳn cho khách chưa đăng nhập, KHÔNG hiện nút
 * disabled/mời đăng nhập (đã xác nhận trước khi code).
 *
 * Không có badge "unread" như thiết kế Collapsed Widget gốc (có chủ đích) -
 * kết nối WebSocket CHỈ mở khi panel mở (tiết kiệm tài nguyên), nên không có
 * cơ chế nhận tin nhắn nào lúc panel đang đóng để mà đếm "chưa đọc".
 */
export function ChatWidget() {
  const { isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const handleServerError = useCallback((message: string) => {
    toast.error(message);
  }, []);

  const { status, messages, sendMessage, retryNow } = useChatSocket({
    enabled: isOpen,
    onServerError: handleServerError,
  });

  if (!isAuthenticated) return null;

  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Mở chat với trợ lý mua sắm Vun"
          className="group relative flex h-16 w-16 items-center justify-center rounded-full bg-primary text-background shadow-warm transition-all hover:scale-105 hover:bg-primary-hover active:scale-95"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
          </svg>
          <div className="pointer-events-none absolute right-full mr-2 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg border border-border bg-surface px-3 py-2 text-xs text-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
            Cần tư vấn mua sắm?
          </div>
        </button>
      </div>
    );
  }

  return (
    <ChatPanel
      messages={messages}
      status={status}
      onSend={sendMessage}
      onRetry={retryNow}
      onClose={() => setIsOpen(false)}
    />
  );
}
