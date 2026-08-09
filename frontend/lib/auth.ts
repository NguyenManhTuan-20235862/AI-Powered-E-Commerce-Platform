/**
 * Lưu trữ và xử lý JWT phía client (localStorage).
 * TODO (Thành viên B - module Auth): chuyển sang httpOnly cookie nếu cần bảo mật cao hơn.
 */

const TOKEN_KEY = "ecommerce_access_token";
const REFRESH_TOKEN_KEY = "ecommerce_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY) ?? window.sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY) ?? window.sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Lưu access + refresh token. persist=true (mặc định) dùng localStorage (giữ sau khi
 * đóng trình duyệt); persist=false dùng sessionStorage (mất khi đóng tab) - dùng khi
 * người dùng không tick "Ghi nhớ đăng nhập".
 */
export function setTokens(accessToken: string, refreshToken: string, options?: { persist?: boolean }): void {
  if (typeof window === "undefined") return;
  const persist = options?.persist ?? true;
  const storage = persist ? window.localStorage : window.sessionStorage;
  const other = persist ? window.sessionStorage : window.localStorage;
  storage.setItem(TOKEN_KEY, accessToken);
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  other.removeItem(TOKEN_KEY);
  other.removeItem(REFRESH_TOKEN_KEY);
}

export function clearTokens(): void {
  removeToken();
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
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
