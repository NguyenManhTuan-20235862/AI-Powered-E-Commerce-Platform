"use client";

import { useEffect, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import type { ChatConnectionStatus, ChatMessageItem } from "@/types/chat";

const STATUS_LABEL: Record<ChatConnectionStatus, string> = {
  idle: "Đang kết nối...",
  connecting: "Đang kết nối...",
  open: "Đang hoạt động",
  reconnecting: "Mất kết nối",
  "retry-exhausted": "Mất kết nối",
};

/**
 * Panel chat (task 5.1.2) - port từ "Expanded Panel (Desktop)" + "Vun - Full
 * Screen Chat (Mobile)". Responsive bằng breakpoint Tailwind (mobile mặc
 * định = full-screen, `md:` override thành panel nổi 380x600) - KHÔNG tách
 * 2 component riêng, đúng pattern `ProductFilters.tsx`/`Header.tsx` đã dùng.
 *
 * Banner "Mất kết nối" CHỈ 1 loại thông báo chung (đúng giới hạn kỹ thuật đã
 * xác nhận trước khi code - trình duyệt không đọc được close code WebSocket
 * thật) - `retry-exhausted` thêm nút "Kết nối lại" thủ công (sau 5 lần tự
 * động retry thất bại, xem useChatSocket.ts).
 */
export function ChatPanel({
  messages,
  status,
  onSend,
  onRetry,
  onClose,
}: {
  messages: ChatMessageItem[];
  status: ChatConnectionStatus;
  onSend: (text: string) => void;
  onRetry: () => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const canSend = status === "open" && draft.trim().length > 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    onSend(draft);
    setDraft("");
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background md:inset-auto md:bottom-6 md:right-6 md:h-[600px] md:w-[380px] md:rounded-[28px] md:border md:border-border md:shadow-warm">
      {/* Header */}
      <div className="flex h-20 shrink-0 items-center justify-between border-b border-border bg-surface px-4 md:rounded-t-[28px] md:px-6">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onClose}
            aria-label="Quay lại"
            className="flex h-10 w-10 items-center justify-center rounded-full text-foreground-secondary hover:bg-primary-100 hover:text-foreground md:hidden"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <div className="flex flex-col">
            <h2 className="font-heading text-lg text-primary">Trợ lý mua sắm Vun</h2>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${status === "open" ? "bg-secondary" : "bg-error"}`}
              />
              <span
                className={`text-xs uppercase tracking-wide ${
                  status === "open" ? "text-foreground-muted" : "text-error"
                }`}
              >
                {STATUS_LABEL[status]}
              </span>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng chat"
          className="hidden h-10 w-10 items-center justify-center rounded-full text-foreground-secondary hover:bg-primary-100 hover:text-foreground md:flex"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {messages.length === 0 ? (
          <div className="my-1 flex justify-center">
            <div className="rounded-full border border-border bg-surface px-4 py-2">
              <p className="text-center text-xs text-foreground-muted">
                Chào bạn! Hãy đặt câu hỏi để Vun hỗ trợ mua sắm nhé.
              </p>
            </div>
          </div>
        ) : (
          messages.map((item) => <ChatMessage key={item.id} item={item} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Disconnect banner + input */}
      <div className="shrink-0 border-t border-border bg-surface p-4 md:rounded-b-[28px]">
        {(status === "reconnecting" || status === "retry-exhausted") && (
          <div className="mb-3 flex items-center justify-between gap-2 rounded-lg bg-error-container px-4 py-2 text-error">
            <p className="text-sm font-semibold">
              {status === "retry-exhausted" ? "Mất kết nối" : "Mất kết nối, đang thử kết nối lại..."}
            </p>
            {status === "retry-exhausted" && (
              <button
                type="button"
                onClick={onRetry}
                className="shrink-0 text-sm font-semibold underline hover:opacity-80"
              >
                Kết nối lại
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={status !== "open"}
            placeholder="Nhập tin nhắn..."
            maxLength={2000}
            aria-label="Nhập tin nhắn cho Vun"
            className="flex-1 rounded-full border border-border bg-background px-4 py-3 text-sm text-foreground placeholder:text-foreground-muted focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Gửi tin nhắn"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 11l18-7-7 18-2-8-9-3z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
