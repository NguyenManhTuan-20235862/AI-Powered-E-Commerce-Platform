# AI-Powered E-Commerce Platform

Nền tảng thương mại điện tử tích hợp AI Agent, hỗ trợ tư vấn sản phẩm, tìm kiếm thông minh
và trải nghiệm mua sắm theo thời gian thực (real-time) thông qua WebSocket/SSE.

Dự án môn học / đồ án nhóm — thực hiện trong 8 tuần bởi nhóm 2 thành viên.

## Mục tiêu

- Xây dựng một nền tảng e-commerce full-stack cơ bản: catalog sản phẩm, giỏ hàng, đơn hàng, tài khoản người dùng.
- Tích hợp AI Agent (LangChain) đóng vai trò trợ lý mua sắm: gợi ý sản phẩm, trả lời câu hỏi, tìm kiếm ngữ nghĩa.
- Cập nhật trạng thái real-time (trạng thái đơn hàng, phản hồi AI dạng streaming) qua WebSocket/SSE.
- Đóng gói toàn bộ hệ thống bằng Docker để chạy nhất quán trên mọi máy.

## Tech Stack

| Thành phần       | Công nghệ                                  |
|-------------------|---------------------------------------------|
| Backend           | FastAPI (Python)                            |
| Frontend          | Next.js (React/TypeScript)                  |
| Cơ sở dữ liệu quan hệ | MySQL (đơn hàng, người dùng, sản phẩm...) |
| Cơ sở dữ liệu tài liệu | MongoDB (log, dữ liệu phi cấu trúc, chat history...) |
| Cache / Message   | Redis                                       |
| AI Agent          | LangChain (+ LLM provider)                  |
| Realtime          | WebSocket / Server-Sent Events (SSE)        |
| Hạ tầng           | Docker, Docker Compose                      |

## Cấu trúc thư mục

```
.
├── backend/          # FastAPI service (API, AI Agent, kết nối MySQL/MongoDB/Redis)
├── frontend/          # Next.js app
├── docs/              # Tài liệu thiết kế, API spec, sơ đồ kiến trúc
├── docker-compose.yml # (sẽ bổ sung) điều phối các service
├── .gitignore
└── README.md
```

## Cách chạy dự án

> Sẽ được bổ sung chi tiết sau khi hoàn thiện `docker-compose.yml`.

Dự kiến:

```bash
# Clone repo
git clone <repo-url>
cd AI-Powered-E-Commerce-Platform

# Chạy toàn bộ hệ thống bằng Docker Compose
docker compose up --build
```

Các service dự kiến:
- `backend` — FastAPI, http://localhost:8000
- `frontend` — Next.js, http://localhost:3000
- `mysql`, `mongodb`, `redis` — chạy nội bộ trong mạng Docker

## Phân công

| Thành viên | Vai trò |
|---|---|
| Thành viên A | Backend (FastAPI, AI Agent, cơ sở dữ liệu) |
| Thành viên B | Frontend (Next.js, giao diện, tích hợp API/WebSocket) |

## Quy ước Git

### Nhánh (Branch)

- `main` — code ổn định, luôn chạy được, chỉ merge qua Pull Request.
- `dev` — nhánh tích hợp chung, các feature merge vào đây trước khi lên `main`.
- `feature/<phạm-vi>-<mô-tả-ngắn>` — nhánh phát triển tính năng, tạo từ `dev`.

Ví dụ:
```
feature/be-product-api
feature/fe-cart-ui
feature/ai-chat-agent
fix/be-order-total-bug
```

Tiền tố gợi ý: `feature/`, `fix/`, `chore/`, `docs/`.

### Commit message (Conventional Commits)

Định dạng: `<type>(<scope>): <mô tả ngắn>`

Các `type` thường dùng:
- `feat` — thêm tính năng mới
- `fix` — sửa lỗi
- `docs` — thay đổi tài liệu
- `style` — định dạng code, không đổi logic
- `refactor` — tái cấu trúc code, không thêm tính năng/sửa lỗi
- `chore` — cấu hình, dependency, công việc phụ trợ
- `test` — thêm/sửa test

Ví dụ:
```
feat(backend): add product listing API
fix(frontend): fix cart total not updating
chore(docker): add docker-compose for mysql and redis
docs(readme): update run instructions
```
