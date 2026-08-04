/**
 * Lưu trữ và xử lý JWT phía client (localStorage).
 * TODO (Thành viên B - module Auth): chuyển sang httpOnly cookie nếu cần bảo mật cao hơn.
 */

const TOKEN_KEY = "ecommerce_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

/** Giải mã payload của JWT (không xác thực chữ ký - chỉ dùng để đọc thông tin ở client). */
export function decodeToken<T = Record<string, unknown>>(token: string): T | null {
  try {
    const payload = token.split(".")[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded) as T;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeToken<{ exp?: number }>(token);
  if (!payload?.exp) return true;
  return Date.now() >= payload.exp * 1000;
}
