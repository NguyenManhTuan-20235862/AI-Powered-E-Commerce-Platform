# API Specification — AI-Powered E-Commerce Platform

**Task WBS:** 1.2.1 — Liệt kê danh sách endpoint cần có
**Phụ trách:** Thành viên A (Backend)
**Base URL (dev):** `http://localhost:8000/api/v1`
**Định dạng response chuẩn:** JSON, bọc trong wrapper `{ "success": bool, "data": ..., "message": str }`
**Auth:** Bearer Token (JWT) trong header `Authorization: Bearer <token>`, trừ các endpoint đánh dấu 🔓 Public

---

## 1. Auth Module (`/auth`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| POST | `/auth/register` | Đăng ký tài khoản Customer | 🔓 Public | - |
| POST | `/auth/login` | Đăng nhập, trả về access token + refresh token | 🔓 Public | - |
| POST | `/auth/refresh` | Làm mới access token bằng refresh token | 🔓 Public | - |
| POST | `/auth/logout` | Đăng xuất, đưa refresh token vào Redis blacklist | 🔒 Auth | Customer, Admin |
| GET | `/auth/me` | Lấy thông tin user hiện tại từ token | 🔒 Auth | Customer, Admin |

---

## 2. User Module (`/users`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/users/me` | Xem thông tin cá nhân | 🔒 Auth | Customer, Admin |
| PUT | `/users/me` | Cập nhật thông tin cá nhân (tên, SĐT, địa chỉ) | 🔒 Auth | Customer, Admin |
| PUT | `/users/me/password` | Đổi mật khẩu | 🔒 Auth | Customer, Admin |
| GET | `/users` | Danh sách toàn bộ user (phân trang, filter) | 🔒 Auth | Admin |
| GET | `/users/{user_id}` | Xem chi tiết 1 user | 🔒 Auth | Admin |
| PUT | `/users/{user_id}/status` | Khóa/mở khóa tài khoản user | 🔒 Auth | Admin |

---

## 3. Product Module (`/products`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/products` | Danh sách sản phẩm (phân trang, filter theo category/giá, search theo tên) | 🔓 Public | - |
| GET | `/products/{product_id}` | Chi tiết 1 sản phẩm | 🔓 Public | - |
| GET | `/products/{product_id}/related` | Sản phẩm liên quan / tương tự (dùng chung logic với AI gợi ý thay thế) | 🔓 Public | - |
| POST | `/products` | Tạo sản phẩm mới | 🔒 Auth | Admin |
| PUT | `/products/{product_id}` | Cập nhật sản phẩm | 🔒 Auth | Admin |
| DELETE | `/products/{product_id}` | Xóa (hoặc ẩn) sản phẩm | 🔒 Auth | Admin |
| POST | `/products/{product_id}/image` | Upload ảnh sản phẩm | 🔒 Auth | Admin |

## 3.1 Category Module (`/categories`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/categories` | Danh sách danh mục sản phẩm | 🔓 Public | - |
| POST | `/categories` | Tạo danh mục mới | 🔒 Auth | Admin |
| PUT | `/categories/{category_id}` | Cập nhật danh mục | 🔒 Auth | Admin |
| DELETE | `/categories/{category_id}` | Xóa danh mục | 🔒 Auth | Admin |

---

## 4. Cart Module (`/cart`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/cart` | Xem giỏ hàng hiện tại | 🔒 Auth | Customer |
| POST | `/cart/items` | Thêm sản phẩm vào giỏ | 🔒 Auth | Customer |
| PUT | `/cart/items/{item_id}` | Cập nhật số lượng sản phẩm trong giỏ | 🔒 Auth | Customer |
| DELETE | `/cart/items/{item_id}` | Xóa sản phẩm khỏi giỏ | 🔒 Auth | Customer |
| DELETE | `/cart` | Xóa toàn bộ giỏ hàng | 🔒 Auth | Customer |

---

## 5. Order Module (`/orders`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| POST | `/orders` | Tạo đơn hàng từ giỏ hàng (transaction trừ tồn kho, có xử lý race condition) | 🔒 Auth | Customer |
| GET | `/orders` | Danh sách đơn hàng của user hiện tại | 🔒 Auth | Customer |
| GET | `/orders/{order_id}` | Chi tiết 1 đơn hàng | 🔒 Auth | Customer (chủ đơn), Admin |
| PUT | `/orders/{order_id}/cancel` | Hủy đơn hàng (nếu đủ điều kiện) | 🔒 Auth | Customer (chủ đơn) |
| GET | `/orders/admin` | Danh sách toàn bộ đơn hàng (filter theo trạng thái, ngày) | 🔒 Auth | Admin |
| PUT | `/orders/{order_id}/status` | Cập nhật trạng thái đơn hàng (xác nhận, đang giao, đã giao) | 🔒 Auth | Admin |

---

## 6. Payment Module (`/payments`) — liên quan task 8.1

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| POST | `/payments/create` | Tạo giao dịch thanh toán (VNPay/Momo sandbox), trả về URL redirect | 🔒 Auth | Customer |
| GET | `/payments/callback` | Nhận callback/IPN từ cổng thanh toán, cập nhật trạng thái Order | 🔓 Public (xác thực bằng chữ ký) | - |
| GET | `/payments/{order_id}/status` | Kiểm tra trạng thái thanh toán của 1 đơn hàng | 🔒 Auth | Customer, Admin |

---

## 7. Review Module (`/reviews`) — MongoDB

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/products/{product_id}/reviews` | Danh sách review của 1 sản phẩm | 🔓 Public | - |
| POST | `/products/{product_id}/reviews` | Viết review (chỉ khi đã mua sản phẩm) | 🔒 Auth | Customer |
| DELETE | `/reviews/{review_id}` | Xóa review vi phạm | 🔒 Auth | Admin |

---

## 8. AI Agent / Chat Module (`/ai`, WebSocket `/ws`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| WS | `/ws/chat` | Kênh WebSocket chat realtime giữa Customer và AI Agent | 🔒 Auth (token qua query/header khi connect) | Customer |
| POST | `/ai/chat` | (Fallback REST) Gửi tin nhắn tới AI Agent, nhận phản hồi | 🔒 Auth | Customer |
| GET | `/ai/chat/history` | Lịch sử hội thoại của user (từ MongoDB ChatLog) | 🔒 Auth | Customer |
| GET | `/ai/chat/logs` | Xem log hội thoại toàn hệ thống (phục vụ tune prompt) | 🔒 Auth | Admin |

**Giới hạn tần suất (task 8.3):** endpoint `/ws/chat` và `/ai/chat` áp dụng rate limit theo user (Redis) — ví dụ tối đa N tin nhắn/phút, trả lỗi `429 Too Many Requests` khi vượt ngưỡng.

---

## 9. Notification / Realtime Module

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| SSE | `/notifications/orders/stream` | Stream sự kiện cập nhật trạng thái đơn hàng realtime | 🔒 Auth | Customer |
| SSE | `/notifications/admin/stream` | Stream sự kiện đơn hàng mới, thống kê realtime cho Admin | 🔒 Auth | Admin |

---

## 10. Dashboard / Statistics Module (`/admin/dashboard`)

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/admin/dashboard/summary` | Tổng quan: tổng doanh thu, số đơn hàng, số user mới | 🔒 Auth | Admin |
| GET | `/admin/dashboard/revenue` | Doanh thu theo ngày/tuần/tháng (dữ liệu cho chart) | 🔒 Auth | Admin |
| GET | `/admin/dashboard/top-products` | Top sản phẩm bán chạy | 🔒 Auth | Admin |

---

## 11. Health Check / System

| Method | Path | Mô tả | Quyền truy cập | Role |
|--------|------|-------|-----------------|------|
| GET | `/health` | Kiểm tra service sống (dùng cho Docker healthcheck, CI/CD) | 🔓 Public | - |
| GET | `/docs` | Swagger UI tự động (FastAPI) | 🔓 Public (dev), có thể tắt ở prod | - |

---

## Ghi chú

- Bảng này là **bản nháp ban đầu** (task 1.2.1) — sẽ được refine thêm khi implement từng module ở các task tiếp theo (1.3, 3.4, 6.x, 8.x...).
- Các endpoint đánh dấu 🔒 Auth đều cần middleware xác thực JWT + kiểm tra role tương ứng (task 1.3.3).
- Sau khi hoàn thiện, cần đồng bộ bảng này với Swagger UI tự động sinh ra ở task 1.2.2 để đảm bảo không lệch giữa tài liệu và code thực tế.
- Naming convention: danh từ số nhiều cho resource (`/products`, `/orders`), dùng path parameter cho ID (`{product_id}`), dùng verb rõ nghĩa cho action đặc biệt (`/cancel`, `/status`).
