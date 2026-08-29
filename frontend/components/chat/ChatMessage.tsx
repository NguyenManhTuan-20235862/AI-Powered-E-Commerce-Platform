import type { ChatMessageItem } from "@/types/chat";

/**
 * Bubble tin nhắn (task 5.1.2) - style thống nhất DÙNG CHUNG cho cả desktop
 * panel lẫn mobile full-screen (2 thiết kế Stitch vẽ hơi khác nhau cho user
 * bubble - desktop dùng tint nhạt, mobile dùng màu đặc - chọn 1 kiểu theo
 * mobile để `ChatPanel.tsx` responsive không cần 2 bộ style riêng).
 *
 * "system" - style pill riêng (khớp `role="system"` Backend luôn dùng cho
 * phản hồi placeholder hiện tại, task 5.1.1) - chưa Backend nào gửi
 * "assistant" (để dành AI thật, task 6.x) nhưng khai đủ style ở đây luôn,
 * không phải sửa lại component khi task đó tới.
 */
export function ChatMessage({ item }: { item: ChatMessageItem }) {
  if (item.role === "system" || item.role === "tool") {
    return (
      <div className="my-1 flex justify-center">
        <div className="rounded-full border border-border bg-surface px-4 py-2">
          <p className="text-center text-xs text-foreground-muted">{item.message}</p>
        </div>
      </div>
    );
  }

  if (item.role === "user") {
    return (
      <div className="mb-3 flex justify-end">
        <div className="max-w-[85%] rounded-3xl rounded-tr-sm bg-primary px-5 py-3 text-background">
          <p className="text-sm">{item.message}</p>
        </div>
      </div>
    );
  }

  // "assistant"
  return (
    <div className="mb-3 flex items-start gap-3">
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary-100 shadow-sm">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="text-secondary">
          <rect x="5" y="8" width="14" height="10" rx="3" />
          <path d="M9 8V6a3 3 0 0 1 6 0v2" strokeLinecap="round" />
          <circle cx="9.5" cy="13" r="1" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="13" r="1" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <div className="max-w-[80%] rounded-3xl rounded-tl-sm border border-border bg-secondary-100 px-5 py-3">
        <p className="text-sm text-foreground">{item.message}</p>
      </div>
    </div>
  );
}
