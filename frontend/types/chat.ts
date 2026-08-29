// Khớp ĐÚNG wire protocol thật của Backend /ws/chat (task 5.1.1,
// backend/app/routers/ai_chat.py) - WebSocket không có OpenAPI nên không tự
// sinh type được, khai tay theo đúng những gì server thật gửi/nhận.

// "assistant" chưa từng được Backend gửi thật (task 6.x mới có AI thật trả
// lời role="assistant") - khai đủ 4 role ngay từ đầu (khớp Literal ở
// backend/app/schemas/chat_log.py) để ChatMessage.tsx không phải sửa lại khi
// task 6.x thay placeholder bằng AI thật.
export type ChatRole = "user" | "assistant" | "system" | "tool";

export interface ChatMessageItem {
  id: string;
  role: ChatRole;
  message: string;
}

// ---- Server -> Client (3 loại event thật, xem chat_websocket() Backend) ----

export interface ChatConnectedEvent {
  type: "connected";
  session_id: string;
}

export interface ChatReplyEvent {
  type: "reply";
  role: "system";
  message: string;
  session_id: string;
}

export interface ChatErrorEvent {
  type: "error";
  message: string;
}

export type ChatServerEvent = ChatConnectedEvent | ChatReplyEvent | ChatErrorEvent;

// ---- Client -> Server (schema ChatMessageCreate, max_length=2000) ----
export interface ChatClientMessage {
  message: string;
}

export type ChatConnectionStatus = "idle" | "connecting" | "open" | "reconnecting" | "retry-exhausted";
