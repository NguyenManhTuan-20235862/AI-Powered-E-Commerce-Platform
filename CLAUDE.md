# CLAUDE.md

Hướng dẫn cho Claude Code khi làm việc trong repo này.

## Project Overview

**AI-Powered E-Commerce Platform** — nền tảng thương mại điện tử tích hợp AI Agent
(tư vấn sản phẩm, tìm kiếm ngữ nghĩa) và cập nhật realtime (trạng thái đơn hàng,
chat AI) qua WebSocket/SSE.

- Dự án cá nhân (solo), thực hiện trong 13 tuần.
- Gồm 2 phần: `backend/` (FastAPI, Python 3.12) và `frontend/` (Next.js 15, TailwindCSS).
- Đặc tả endpoint chi tiết: [`docs/API_SPEC.md`](docs/API_SPEC.md) — **đọc file này
  trước khi thêm/sửa route** để đảm bảo path, tag, quyền truy cập khớp với thiết kế.

## Tech Stack

Liệt kê đúng theo `backend/requirements.txt` và `frontend/package.json` — không có
gì ngoài danh sách này đang thực sự được dùng trong code.

**Backend** (`backend/requirements.txt`):
- FastAPI 0.115 + Uvicorn (ASGI server)
- Pydantic 2.10 + pydantic-settings (đọc config từ `.env`)
- SQLAlchemy 2.0 + Alembic (ORM + migration cho MySQL) + PyMySQL (driver)
- PyMongo 4.10 (MongoDB - chat log, review)
- redis-py 5.2 (cache, session, rate limit)
- python-jose + passlib[bcrypt] (JWT, hash password) — **đã khai báo dependency
  nhưng logic JWT thật CHƯA implement**, xem phần Notes.
- python-multipart (form-data / upload file)
- email-validator (bắt buộc để dùng `EmailStr` trong Pydantic)
- LangChain + langchain-openai — **đã khai báo dependency nhưng CHƯA có code
  tích hợp AI Agent nào trong `app/`**
- pytest + httpx (test)

**Frontend** (`frontend/package.json`):
- Next.js 15 (App Router) + React 19
- Axios (gọi API)
- TailwindCSS 3.4 + PostCSS + Autoprefixer
- TypeScript 5, ESLint 9 + eslint-config-next

**Chưa có trong repo** (đừng giả định tồn tại): `docker-compose.yml`, `Makefile`,
Dockerfile, CI config, linter/formatter cho backend (không có ruff/black), test
nào cho frontend.

## Commands

**Backend** (`cd backend`, cần Python 3.12 + venv):
```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env          # rồi điền giá trị thật, KHÔNG commit .env
uvicorn app.main:app --reload  # dev server: http://localhost:8000
pytest -q                       # chạy test
```
Swagger UI: `http://localhost:8000/docs` (tự ẩn khi `APP_ENV=production`).

**Frontend** (`cd frontend`):
```bash
npm install
npm run dev     # dev server: http://localhost:3000
npm run build   # production build
npm run start   # chạy bản build
npm run lint    # eslint
```

**Docker**: chưa có `docker-compose.yml` trong repo — README có nhắc "sẽ bổ sung
sau", nên hiện tại KHÔNG có lệnh `docker compose up` nào chạy được. Khi file này
được thêm, cập nhật lại mục này.

## Architecture

**Backend** (`backend/app/`) — chia theo layer, file đặt tên theo domain trong
mỗi layer (khớp `docs/API_SPEC.md`):
```
app/
├── main.py           # khởi tạo FastAPI, CORS, OpenAPI tags, include router
├── core/
│   ├── config.py          # Settings (pydantic-settings, đọc .env)
│   ├── database.py        # engine MySQL, MongoClient, Redis client
│   ├── security.py        # get_current_user (JWT — hiện là dependency GIẢ, xem Notes)
│   └── openapi_responses.py  # helper responses={401,403,404,429} dùng chung
├── routers/           # 1 file/module: auth, user, product, category, cart,
│                        order, payment, review, ai_chat, notification, dashboard
├── models/             # SQLAlchemy models (MySQL) — hiện là placeholder, chưa có cột
├── schemas/            # Pydantic schemas, gồm common.py (envelope response chuẩn)
└── services/            # business logic tách khỏi router — hiện là placeholder
```

**Frontend** (`frontend/app/`) — App Router, chia theo route group:
```
app/
├── (customer)/    # route group: Header/Footer, "/" "/products" "/cart"...
├── (auth)/         # route group: layout căn giữa, "/login" "/register"
└── admin/           # segment THẬT (không phải route group) → "/admin/*"
                       # (tránh trùng URL với (customer)/products)
```
`lib/axios.ts` (interceptor gắn JWT), `lib/auth.ts` (đọc/ghi token localStorage),
`hooks/useAuth.ts`, `types/` (User/Product/Order/Cart).

**Luồng dữ liệu chính**:
- **MySQL** (qua SQLAlchemy): dữ liệu quan hệ — User, Product, Category, Cart, Order.
- **MongoDB** (qua PyMongo): dữ liệu phi cấu trúc — Chat log (AI Agent), Review.
- **Redis**: cache, session/token blacklist khi logout, **rate limit cho AI chat**
  (`/ai/chat`, `/ws/chat` — xem `docs/API_SPEC.md` mục 8).

## Coding Conventions

- **Backend**: `snake_case` cho file/hàm Python, `PascalCase` cho class Pydantic/
  SQLAlchemy. Mỗi router gắn đúng `prefix`/`tags` theo `docs/API_SPEC.md`. Toàn bộ
  response dữ liệu bọc trong envelope `APIResponse[T]` (`app/schemas/common.py`):
  `{ "success": bool, "data": ..., "message": str }`. Endpoint chưa implement dùng
  `raise HTTPException(status_code=501)`, không `return` dict tùy tiện (tránh lệch
  với `response_model` đã khai báo).
- **Frontend**: component `PascalCase` (`Header.tsx`), hook/hàm `camelCase`
  (`useAuth.ts`), Tailwind utility-first. Chỉ thêm `"use client"` khi thật sự cần
  CSR (state, event handler, browser API) — mặc định Server Component.
- **Commit message**: Conventional Commits — `<type>(<scope>): <mô tả>`, type gồm
  `feat|fix|docs|style|refactor|chore|test`. Chi tiết + quy ước branch: xem README.

## Notes

- **Đọc `docs/API_SPEC.md` trước khi thêm route mới** — đây là nguồn sự thật cho
  path/method/tag/quyền truy cập (Public/Auth/Role). Nếu code lệch spec, đồng bộ
  lại 1 trong 2 phía, đừng để lệch âm thầm.
- **Không commit `.env` thật** — `.gitignore` đã chặn `.env`/`.env.*` (trừ
  `.env.example`). Luôn cập nhật `.env.example` khi thêm biến môi trường mới.
- **`get_current_user` hiện là dependency GIẢ** (`backend/app/core/security.py`) —
  chỉ kiểm tra có Bearer token hay không (401 nếu thiếu), luôn trả về
  `role="customer"`, KHÔNG decode JWT thật. Đừng dựa vào role trả về từ đây cho
  logic thật; sẽ được thay bằng JWT decode thật ở task xác thực.
- **Rate limit AI chat dùng Redis** — `/ai/chat` và `/ws/chat` cần giới hạn tần suất
  theo user (xem `docs/API_SPEC.md` mục 8), hiện CHƯA implement, chỉ mới khai báo
  response `429` trong docs.
- **WebSocket không xuất hiện trên Swagger UI** — giới hạn của chuẩn OpenAPI, không
  phải lỗi cấu hình.
- Route `/orders/admin` (path cố định) được đăng ký TRƯỚC `/orders/{order_id}`
  trong `app/routers/order.py` — nếu thêm route mới có path cố định xen giữa các
  route templated, giữ đúng thứ tự này để tránh bị route templated nuốt mất.
