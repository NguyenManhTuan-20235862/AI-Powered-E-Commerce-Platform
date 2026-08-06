import { AxiosError } from "axios";

/**
 * Shape giả định theo docs/API_SPEC.md cho response lỗi:
 *   { success: false, message: string, errors?: { field: string, message: string }[] }
 */
type ApiErrorBody = {
  success?: boolean;
  message?: string;
  errors?: { field: string; message: string }[];
};

export function extractFieldError(err: unknown, field: string): string | undefined {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.errors?.find((e) => e.field === field)?.message;
  }
  return undefined;
}

/** Message chung, an toàn cho người dùng - không lộ status code hay stack trace. */
export function genericAuthErrorMessage(err: unknown, context: "login" | "register"): string {
  if (err instanceof AxiosError) {
    if (!err.response) return "Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng và thử lại.";
    if (err.response.status === 429) return "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.";
    if (context === "login" && err.response.status === 401) {
      return "Email hoặc mật khẩu không đúng. Vui lòng kiểm tra lại.";
    }
    const body = err.response.data as ApiErrorBody | undefined;
    if (body?.message && body.message.length < 140) return body.message;
  }
  return context === "login"
    ? "Đăng nhập thất bại. Vui lòng thử lại."
    : "Tạo tài khoản thất bại. Vui lòng thử lại.";
}
