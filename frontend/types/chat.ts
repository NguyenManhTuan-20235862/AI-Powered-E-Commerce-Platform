// Khớp ĐÚNG wire protocol thật của Backend /ws/chat (task 5.1.1, agent thật +
// streaming task 6.1.2, backend/app/routers/ai_chat.py) - WebSocket không có
// OpenAPI nên không tự sinh type được, khai tay theo đúng những gì server
// thật gửi/nhận.

// "system"/"tool" giữ lại dù Backend hiện KHÔNG còn gửi "system" nữa (đã bỏ
// hẳn placeholder task 5.1.1, thay bằng "assistant" thật task 6.1.2) - khớp
// đủ Literal ở backend/app/schemas/chat_log.py (lịch sử cũ trong MongoDB có
// thể vẫn còn role "system" nếu sau này có API đọc lại - ChatMessage.tsx vẫn
// cần biết style cho role này).
export type ChatRole = "user" | "assistant" | "system" | "tool";

export interface ChatMessageItem {
  id: string;
  role: ChatRole;
  message: string;
}

// ---- Server -> Client (4 loại event thật, xem chat_websocket() Backend) ----

export interface ChatConnectedEvent {
  type: "connected";
  session_id: string;
}

// Task 6.1.2 - streaming: 1 event/mảnh text AI vừa sinh ra, bắn LIÊN TỤC cho
// 1 lượt trả lời - client nối dần `content` vào tin nhắn assistant đang hiện
// (xem useChatSocket.ts), KHÔNG PHẢI 1 tin nhắn hoàn chỉnh như "reply" cũ
// (đã bỏ hẳn, xem lịch sử git nếu cần đối chiếu).
export interface ChatChunkEvent {
  type: "chunk";
  content: string;
}

// Task 6.1.2 - báo 1 lượt trả lời đã stream xong (KHÔNG kèm nội dung - client
// đã có đủ từ các "chunk" cộng dồn) - dùng để mở khóa lại input/nút gửi.
export interface ChatDoneEvent {
  type: "done";
}

export interface ChatErrorEvent {
  type: "error";
  message: string;
}

export type ChatServerEvent = ChatConnectedEvent | ChatChunkEvent | ChatDoneEvent | ChatErrorEvent;

// ---- Client -> Server (schema ChatMessageCreate, max_length=2000) ----
export interface ChatClientMessage {
  message: string;
}

export type ChatConnectionStatus = "idle" | "connecting" | "open" | "reconnecting" | "retry-exhausted";
