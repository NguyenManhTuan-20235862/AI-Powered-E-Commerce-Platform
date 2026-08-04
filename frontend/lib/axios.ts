import axios from "axios";

import { getToken } from "./auth";

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

// TODO (Thành viên B): thêm response interceptor xử lý 401 (redirect /login, xóa token...)
// khi module Auth hoàn thiện ở tuần sau.

export default api;
