import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, refreshApi } from "@/lib/axios";

/**
 * Test THẬT cho interceptor 401 (`lib/axios.ts`, task "Dọn frontend để
 * không còn màn hình giả" - thống nhất xử lý 401). Dùng `adapter` tùy biến
 * (thay HTTP thật) thay vì mock `axios` module.
 *
 * QUAN TRỌNG: 1 `adapter` axios đơn thuần KHÔNG tự reject theo `status` ngoài
 * `validateStatus` - hành vi đó (`settle()`) nằm BÊN TRONG từng adapter THẬT
 * (`http.js`/`xhr.js`), không phải ở tầng `dispatchRequest` dùng chung (đã tự
 * gặp lúc viết test này: adapter resolve `{status: 401}` thẳng vẫn được axios
 * coi là THÀNH CÔNG, không lọt vào response interceptor lỗi nào cả) - adapter
 * giả ở đây PHẢI tự làm bước `settle` này (`respond()` bên dưới, throw
 * `AxiosError` thật khi status ngoài 2xx) để tái hiện đúng hành vi network thật.
 *
 * `window.location` bị xóa + gán lại object giả (`delete` + gán mới) - cách
 * DUY NHẤT ghi được `.href` trong jsdom (jsdom định nghĩa `location` là
 * accessor không cho gán trực tiếp).
 */

const TOKEN_KEY = "ecommerce_access_token";
const REFRESH_TOKEN_KEY = "ecommerce_refresh_token";

let originalLocation: Location;

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  originalLocation = window.location;
  // @ts-expect-error - test-only: jsdom location là accessor, phải xóa trước khi gán lại.
  delete window.location;
  // @ts-expect-error - test-only stub, chỉ cần field href.
  window.location = { href: "" };
});

afterEach(() => {
  window.location = originalLocation;
  api.defaults.adapter = undefined;
  refreshApi.defaults.adapter = undefined;
  vi.restoreAllMocks();
});

/** Mô phỏng 1 response HTTP thật đi qua `validateStatus` (mặc định 200-299) -
 * status ngoài khoảng này throw `AxiosError` thật (kèm `.response` đầy đủ),
 * đúng hành vi 1 adapter axios thật (xem giải thích ở docstring đầu file). */
function respond(config: InternalAxiosRequestConfig, status: number, data: unknown): AxiosResponse {
  const response: AxiosResponse = {
    data,
    status,
    statusText: status >= 200 && status < 300 ? "OK" : "Error",
    headers: {},
    config,
  };
  if (status >= 200 && status < 300) return response;
  throw new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_REQUEST, config, undefined, response);
}

/** Đợi 1 khoảng NGẮN thật (không dùng fake timer - promise "bỏ rơi" không
 * bao giờ tự resolve nên không có gì để advance) rồi xác nhận promise vẫn
 * CHƯA settle (KHÔNG resolve, KHÔNG reject) - bằng cách race với 1 promise
 * timeout, chỉ promise nào xong TRƯỚC mới thắng race. */
async function expectNeverSettles(promise: Promise<unknown>): Promise<void> {
  const TIMEOUT = Symbol("timeout");
  const settled = promise.then(
    () => "resolved",
    () => "rejected",
  );
  const result = await Promise.race([settled, new Promise((resolve) => setTimeout(() => resolve(TIMEOUT), 40))]);
  expect(result).toBe(TIMEOUT);
}

describe("lib/axios.ts - interceptor 401 (thống nhất xử lý, task dọn frontend)", () => {
  it("401, KHÔNG có refresh token, KHÔNG skipAuthRedirect - điều hướng /login?session_expired=1, promise KHÔNG BAO GIỜ settle", async () => {
    api.defaults.adapter = vi.fn(async (config) => respond(config, 401, { success: false, message: "Thiếu token" }));

    const request = api.get("/orders/1");

    await expectNeverSettles(request);
    expect(window.location.href).toBe("/login?session_expired=1");
  });

  it("401, KHÔNG có refresh token, CÓ skipAuthRedirect - reject bình thường, KHÔNG điều hướng", async () => {
    api.defaults.adapter = vi.fn(async (config) => respond(config, 401, { success: false, message: "Thiếu token" }));

    await expect(api.get("/auth/me", { skipAuthRedirect: true })).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(window.location.href).toBe("");
  });

  it("401 rồi refresh THÀNH CÔNG - tự retry lại request gốc với access token mới, KHÔNG điều hướng", async () => {
    window.localStorage.setItem(TOKEN_KEY, "old-access-token");
    window.localStorage.setItem(REFRESH_TOKEN_KEY, "valid-refresh-token");

    let callCount = 0;
    api.defaults.adapter = vi.fn(async (config) => {
      callCount += 1;
      // Lần gọi ĐẦU (access token cũ) -> 401; lần RETRY (sau refresh, header
      // Authorization đã đổi) -> 200 với dữ liệu thật.
      if (callCount === 1) {
        expect(config.headers.Authorization).toBe("Bearer old-access-token");
        return respond(config, 401, { success: false, message: "Hết hạn" });
      }
      expect(config.headers.Authorization).toBe("Bearer new-access-token");
      return respond(config, 200, { success: true, message: "", data: { id: 1 } });
    });
    refreshApi.defaults.adapter = vi.fn(async (config) =>
      respond(config, 200, {
        success: true,
        message: "",
        data: { access_token: "new-access-token", refresh_token: "new-refresh-token" },
      }),
    );

    const { data } = await api.get("/orders/1");

    expect(data.data).toEqual({ id: 1 });
    expect(callCount).toBe(2);
    expect(window.location.href).toBe("");
    // Access token mới phải được lưu lại ĐÚNG storage cũ (localStorage, vì
    // access token cũ ở trên cũng đặt vào localStorage - "Ghi nhớ đăng nhập").
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("new-access-token");
  });

  it("401 rồi refresh THẤT BẠI (refresh token cũng hết hạn/bị revoke) - điều hướng /login?session_expired=1, promise KHÔNG BAO GIỜ settle", async () => {
    window.localStorage.setItem(TOKEN_KEY, "old-access-token");
    window.localStorage.setItem(REFRESH_TOKEN_KEY, "dead-refresh-token");

    api.defaults.adapter = vi.fn(async (config) => respond(config, 401, { success: false, message: "Hết hạn" }));
    refreshApi.defaults.adapter = vi.fn(async (config) => respond(config, 401, { success: false, message: "Refresh token không hợp lệ" }));

    const request = api.get("/orders/1");

    await expectNeverSettles(request);
    expect(window.location.href).toBe("/login?session_expired=1");
  });

  it("401 ở /auth/login - reject thẳng (sai email/mật khẩu), KHÔNG thử refresh/điều hướng", async () => {
    api.defaults.adapter = vi.fn(async (config) => respond(config, 401, { success: false, message: "Sai email hoặc mật khẩu" }));

    await expect(api.post("/auth/login", { email: "a@b.com", password: "x" })).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(window.location.href).toBe("");
  });
});
