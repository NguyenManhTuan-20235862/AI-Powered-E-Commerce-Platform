import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { clearTokens, getRefreshToken, getToken, isTokenPersisted, setTokens } from "./auth";

// Custom field (không gửi qua network, chỉ đọc lại ở response interceptor
// bên dưới) - đánh dấu request KHÔNG nên bị điều hướng cứng sang "/login" nếu
// refresh thất bại. Dùng cho lần gọi GET /auth/me NỀN lúc AuthProvider mount
// (context/AuthContext.tsx) - đây là kiểm tra THỤ ĐỘNG chạy trên MỌI trang kể
// cả trang công khai (home, catalog...), không nên đá user đang xem trang
// công khai sang /login chỉ vì có sẵn token cũ/hết hạn từ nhiều ngày trước
// trong localStorage. Guard THẬT (AdminAuthGuard, /cart, /checkout, /orders)
// tự đọc `isAuthenticated=false` từ AuthContext để điều hướng, đúng đúng chỗ
// cần điều hướng hơn là điều hướng ngầm từ tầng HTTP client.
declare module "axios" {
  export interface AxiosRequestConfig {
    skipAuthRedirect?: boolean;
  }
}

/**
 * Axios instance dùng chung cho toàn bộ app.
 * Tự động gắn JWT (nếu có) vào header Authorization của mỗi request.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Instance RIÊNG, KHÔNG gắn interceptor nào - chỉ dùng để gọi POST /auth/refresh
// từ BÊN TRONG response interceptor dưới đây. Dùng lại `api` (có cùng interceptor)
// sẽ tự đệ quy vào chính interceptor này mỗi khi refresh thất bại (401) - vẫn
// thoát được nhờ nhánh loại trừ URL, nhưng gọi redirectToLogin() 2 lần không
// cần thiết; instance riêng đơn giản hơn, không có rủi ro đệ quy nào cả.
const refreshApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
});

type RefreshApiResponse = {
  data: { access_token: string; refresh_token: string };
};

// Nhiều request cùng 401 gần như đồng thời (VD trang mở nhiều API song song
// lúc mount) CHỈ nên gọi POST /auth/refresh ĐÚNG 1 LẦN - các request 401 tới
// sau trong lúc đang refresh phải CHỜ kết quả của lần refresh đang chạy rồi
// tự retry với access token mới, không tự gọi refresh riêng (tốn round-trip,
// và refresh token có thể đã bị đổi/blacklist khiến lần gọi sau thất bại oan).
let refreshPromise: Promise<string> | null = null;

function redirectToLogin(): void {
  clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retriedAfterRefresh?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableConfig | undefined;

    if (!originalRequest || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const url = originalRequest.url ?? "";
    // /auth/login, /auth/register: 401/400 ở đây là "sai email/mật khẩu" thật,
    // không phải access token hết hạn - không có access token nào để refresh.
    // /auth/refresh: xử lý riêng ở nhánh catch bên dưới (gọi qua refreshApi).
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/register");
    if (isAuthEndpoint || originalRequest._retriedAfterRefresh) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      if (!originalRequest.skipAuthRedirect) redirectToLogin();
      return Promise.reject(error);
    }

    originalRequest._retriedAfterRefresh = true;

    try {
      if (!refreshPromise) {
        refreshPromise = refreshApi
          .post<RefreshApiResponse>("/auth/refresh", { refresh_token: refreshToken })
          .then(({ data }) => {
            const { access_token, refresh_token } = data.data;
            setTokens(access_token, refresh_token, { persist: isTokenPersisted() });
            return access_token;
          })
          .finally(() => {
            refreshPromise = null;
          });
      }
      const newAccessToken = await refreshPromise;
      originalRequest.headers = originalRequest.headers ?? {};
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      if (!originalRequest.skipAuthRedirect) redirectToLogin();
      return Promise.reject(refreshError);
    }
  },
);

export default api;
