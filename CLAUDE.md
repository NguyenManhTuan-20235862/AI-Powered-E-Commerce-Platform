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

Liệt kê đúng theo `backend/requirements-core.txt` + `backend/requirements-ai.txt`
+ `backend/requirements-test.txt` + `backend/requirements-prod.txt` và
`frontend/package.json` — không có gì ngoài danh sách này đang thực sự được
dùng trong code.

**Backend** (`backend/requirements-core.txt` — cài mặc định, kể cả trong
`Dockerfile.dev` VÀ `Dockerfile.prod`):
- FastAPI 0.115 + Uvicorn (ASGI server)
- Pydantic 2.10 + pydantic-settings (đọc config từ `.env`)
- SQLAlchemy 2.0 + Alembic (ORM + migration cho MySQL) + PyMySQL (driver)
- PyMongo 4.10 (MongoDB - chat log, review)
- redis-py 5.2 (cache, session, rate limit)
- python-jose + passlib[bcrypt] (JWT, hash password - đã implement thật từ task 1.3.3)
- python-multipart (form-data / upload file)
- email-validator (bắt buộc để dùng `EmailStr` trong Pydantic)

**Backend** (`backend/requirements-ai.txt` — CHƯA cài mặc định, xem Notes):
- LangChain + langchain-openai — tách riêng khỏi requirements-core.txt vì CHƯA
  có code tích hợp AI Agent nào trong `app/`; cài kèm khi bắt đầu task 6.x.

**Backend** (`backend/requirements-test.txt` — cài trong `Dockerfile.dev`,
KHÔNG cài trong `Dockerfile.prod`, task 2.1.2):
- pytest + httpx (test) — production không cần test framework lúc chạy thật.

**Backend** (`backend/requirements-prod.txt` — CHỈ cài trong `Dockerfile.prod`,
task 2.1.2):
- Gunicorn (process manager, chạy Uvicorn worker) — dev dùng `uvicorn --reload`
  trực tiếp, không cần Gunicorn.

**Frontend** (`frontend/package.json`):
- Next.js 15 (App Router) + React 19
- Axios (gọi API)
- TailwindCSS 3.4 + PostCSS + Autoprefixer
- TypeScript 5, ESLint 9 + eslint-config-next

**Chưa có trong repo** (đừng giả định tồn tại): `Makefile`, CI config, linter/
formatter cho backend (không có ruff/black), test nào cho frontend.
`docker-compose.yml` (gốc repo, task 2.3.1 → 2.3.4 + 3.5.2) đã ĐỦ 6 service
(`mysql`, `mongodb`, `redis`, `backend`, `frontend`, `product-sync-scheduler`)
- `docker compose up` (không chỉ định service) giờ chạy được TOÀN BỘ stack
bằng 1 lệnh, xem Commands. Vẫn CHƯA có: file compose riêng cho production
(Dockerfile.prod của Backend/Frontend chưa được dùng ở đâu cả, đó là việc
khác - task deploy sau này).

**`product-sync-scheduler`** (task 3.5.2, `backend/scripts/run_scheduler.py`)
- tiến trình APScheduler ĐỘC LẬP, KHÔNG chung process với `backend`
(Gunicorn/API) - dùng lại NGUYÊN `Dockerfile.dev`/`Dockerfile.prod` của
Backend (chỉ đổi `command:` để chạy `python -m scripts.run_scheduler` thay vì
uvicorn/gunicorn), chạy `sync_products_to_mongo()` (task 3.5.1) theo lịch cron
đọc từ `PRODUCT_SYNC_CRON` (mặc định `0 2 * * *`, giờ Việt Nam). Tách container
riêng (không nhúng APScheduler vào `app/main.py`) để tránh N Gunicorn worker
của `backend` production mỗi worker tự chạy 1 bản lịch riêng (sync trùng N
lần mỗi khi tới giờ) - luôn ĐÚNG 1 tiến trình chạy scheduler bất kể `backend`
có bao nhiêu worker. Lỗi trong lúc sync (MySQL/Mongo tạm thời không kết nối
được...) chỉ log, KHÔNG crash scheduler - tự chờ lịch chạy kế tiếp. Trigger
chạy tay (test/verify): `docker compose exec product-sync-scheduler python -m
scripts.sync_products_to_mongo` - CỐ TÌNH không có endpoint HTTP cho việc
này, xem lý do đầy đủ trong docstring `run_scheduler.py`.

`nginx/nginx.conf` (task 2.4.1) đã có - routing `/` → `frontend:3000`, `/api/`
→ `backend:8000` (giữ nguyên path, KHÔNG strip `/api` - khớp `API_PREFIX =
"/api/v1"` đã gắn cứng trong `app/main.py`, áp dụng cho MỌI router kể cả
`/ws/chat` và `/notifications/*/stream` - path thật là `/api/v1/ws/chat`,
KHÔNG PHẢI `/ws/chat` trơ dù cách đọc lướt `docs/API_SPEC.md` dễ hiểu nhầm).
**CHƯA đưa nginx vào `docker-compose.yml`** (quyết định có chủ đích, xem
`docs/KNOWN_TODOS.md` nếu có ghi chú thêm) - dev vẫn truy cập trực tiếp
`:3000`/`:8000` như từ task 2.3.4, `nginx/nginx.conf` hiện chỉ test độc lập
bằng container tạm (xem Commands).

## Commands

**Docker Compose - CÁCH CHẠY DEV KHUYẾN NGHỊ** (`docker-compose.yml` ở gốc
repo, đủ 6 service từ task 2.3.4/3.5.2 - dùng `Dockerfile.dev` cho cả Backend
lẫn Frontend (và `product-sync-scheduler`, dùng lại Dockerfile.dev của
Backend), có hot-reload qua volume mount, KHÔNG phải bản tối ưu production):
```bash
cp .env.example .env                  # gốc repo - MYSQL_ROOT_PASSWORD/MYSQL_DATABASE +
                                        # MONGO_INITDB_ROOT_USERNAME/PASSWORD + REDIS_PASSWORD
cp backend/.env.example backend/.env  # JWT_SECRET_KEY + các biến khác Backend cần lúc chạy
                                        # standalone - 3 biến DATABASE_URL/MONGO_URI/REDIS_URL
                                        # trong file này bị docker-compose.yml OVERRIDE tự động
                                        # khi chạy qua compose (đổi host -> tên service), KHÔNG
                                        # cần tự sửa 3 biến đó cho khớp compose.
docker compose up --build     # build + chạy CẢ 6 service - MySQL/MongoDB/Redis lên trước
                                # (đợi healthy), Backend + product-sync-scheduler lên sau (đợi
                                # DB healthy - scheduler chỉ cần mysql+mongodb, không đợi redis),
                                # Frontend lên cuối (đợi Backend healthy) - đúng thứ tự tự động
                                # qua `depends_on: condition: service_healthy`.
docker compose ps             # xem trạng thái + healthcheck từng service
docker compose logs -f backend    # xem log riêng 1 service (tương tự frontend/mysql/...)
docker compose down           # dừng - GIỮ NGUYÊN data MySQL/MongoDB (named volume), Redis
                                # LUÔN mất (tmpfs, chủ đích - xem docker-compose.yml)
docker compose down -v        # dừng + XÓA LUÔN volume MySQL/MongoDB - mất toàn bộ data
```
Truy cập: Frontend `http://localhost:3000`, Backend/Swagger `http://localhost:8000/docs`,
MySQL/MongoDB/Redis vẫn publish port ra host (3306/27017/6379) để debug bằng
Workbench/Compass/RedisInsight nếu cần, dù Backend/Frontend không dùng các port
này (gọi nhau qua tên service trong network nội bộ compose).

**Backend standalone** (`cd backend`, cần Python 3.12 + venv - dùng khi muốn
chạy Backend NGOÀI Docker, VD cần chạy `pytest` nhanh không qua container,
hoặc debug bằng debugger gắn trực tiếp vào process):
```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-core.txt -r requirements-test.txt   # + requirements-ai.txt khi làm task 6.x
cp .env.example .env          # rồi điền giá trị thật, KHÔNG commit .env
uvicorn app.main:app --reload  # dev server: http://localhost:8000
pytest -q                       # chạy test
```
Swagger UI: `http://localhost:8000/docs` (tự ẩn khi `APP_ENV=production`).

**Frontend standalone** (`cd frontend` - dùng khi muốn chạy Frontend NGOÀI Docker):
```bash
npm install
npm run dev     # dev server: http://localhost:3000
npm run build   # production build
npm run start   # chạy bản build
npm run lint    # eslint
```

**Test `nginx/nginx.conf`** (task 2.4.1 - CHƯA có service `nginx` trong
`docker-compose.yml`, test độc lập bằng container tạm):
```bash
# Kiểm tra cú pháp - PHẢI gắn --network vào network của compose (tên network =
# <tên-thư-mục-project>_default, xem `docker network ls`) để hostname
# backend/frontend resolve được thật - nginx -t VẪN CÓ THỂ báo "syntax ok" dù
# hostname không resolve được nếu chạy ngoài network (đã tự gặp: DNS lạ trên
# máy Windows "bắt" luôn hostname không tồn tại, nginx -t tưởng nhầm là hợp
# lệ) - gắn đúng network là cách kiểm tra ĐÁNG TIN CẬY duy nhất.
docker compose up -d   # đảm bảo cả 6 service đang chạy trước
MSYS_NO_PATHCONV=1 docker run --rm \
  --network ai-powered-e-commerce-platform_default \
  -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  nginx:1.27-alpine nginx -t

# Test thật (map port 8080 host -> 80 nginx, tránh đụng port 3000/8000 đang
# publish trực tiếp):
MSYS_NO_PATHCONV=1 docker run -d --name nginx-test \
  --network ai-powered-e-commerce-platform_default \
  -p 8080:80 \
  -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  nginx:1.27-alpine
curl -i -X OPTIONS http://localhost:8080/api/v1/auth/login   # -> qua nginx tới backend
                                                                # (chú ý: /health KHÔNG có prefix
                                                                # /api/v1, xem app/main.py - dùng route
                                                                # có thật dưới /api/v1/ để test, VD trên)
curl http://localhost:8080/                                   # -> qua nginx tới frontend
docker rm -f nginx-test                    # dọn sau khi test xong
```

## Architecture

**Backend** (`backend/app/`) — chia theo layer, file đặt tên theo domain trong
mỗi layer (khớp `docs/API_SPEC.md`):
```
app/
├── main.py           # khởi tạo FastAPI, CORS, OpenAPI tags, include router
├── core/
│   ├── config.py          # Settings (pydantic-settings, đọc .env)
│   ├── database.py        # engine MySQL, MongoClient, Redis client
│   ├── security.py        # get_current_user (decode JWT thật, require_role — xem Notes)
│   ├── cache.py            # get_or_set_cache()/invalidate_by_prefix() (Redis, task 3.3.1/3.4.1)
│   ├── storage.py          # lưu ảnh upload local (task 3.4.1 — xem Notes)
│   └── openapi_responses.py  # helper responses={401,403,404,429} dùng chung
├── routers/           # 1 file/module: auth, user, product, category, cart,
│                        order, payment, review, ai_chat, notification, dashboard
├── models/             # SQLAlchemy models (MySQL) — đủ cột thật (User task 1.3.1,
│                        Category/Product task 3.1.2, CartItem/Order/OrderItem/
│                        Payment task 3.1.3), migrate qua Alembic (task 3.1.4)
├── schemas/            # Pydantic schemas, gồm common.py (envelope response chuẩn)
└── services/            # business logic tách khỏi router — auth/product/cart/order
                           đã có logic thật (task 1.3.2, 3.4.1, 3.4.2); category/
                           dashboard/payment vẫn placeholder (chưa tới task tương ứng)
```

**Frontend** (`frontend/app/`) — App Router, chia theo route group:
```
app/
├── (customer)/    # route group: Header/Footer, "/" "/products" "/cart"...
├── (auth)/         # route group: layout 2 cột full-bleed riêng, "/login" "/register"
└── admin/           # segment THẬT (không phải route group) → "/admin/*"
                       # (tránh trùng URL với (customer)/products)
```
`lib/axios.ts` (interceptor gắn JWT), `lib/auth.ts` (đọc/ghi token localStorage),
`hooks/useAuth.ts`, `types/` (User/Product/Order/Cart).

**Design token** (task 4.1.1, xem `docs/DESIGN_TOKENS.md`) — màu/font/radius/
shadow khai báo 1 lần dạng CSS custom property ở `app/globals.css` (`:root`),
`tailwind.config.ts` map thành class ngữ nghĩa (`bg-primary`, `bg-surface`,
`text-foreground`, `font-heading`...) TRỎ THẲNG vào cùng biến đó — không lặp
lại giá trị hex. Component mới (catalog, admin...) dùng thẳng class Tailwind
này; `app/(auth)/auth.css` (CSS thuần, không phải Tailwind utility, viết từ
task 1.3.4) vẫn giữ nguyên cách viết cũ, chỉ đọc chung biến `--color-*`/
`--font-*` từ `globals.css` thay vì tự khai báo `:root` riêng.

**`NEXT_PUBLIC_API_URL` luôn phải là URL truy cập được từ trình duyệt** (VD:
`http://localhost:8000/api/v1`) — **KHÔNG BAO GIỜ** dùng tên service Docker
(`http://backend:8000`) hay `host.docker.internal`, kể cả sau khi có
`docker-compose.yml` ở task 2.3. Lý do: biến `NEXT_PUBLIC_*` được Next.js nhúng
thẳng vào bundle JS chạy ở **trình duyệt người dùng** (client-side), không phải
chạy trong container - trình duyệt trên máy host không resolve được tên service
Docker lẫn `host.docker.internal` (hostname đó chỉ có nghĩa bên trong network
namespace của Docker). Khác với các biến phía Backend (server-side, chỉ chạy
trong container) - những biến đó mới dùng được tên service/`host.docker.internal`.
Xem thêm task 2.2.1.

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
- **Không commit `.env` thật** — `.gitignore` (gốc repo VÀ `frontend/.gitignore`,
  cả 2 đã sửa ở task 2.4.2 - trước đó `frontend/.env.example` bị chặn nhầm,
  chưa từng commit được) chặn `.env`/`.env.*`, CHỈ cho phép `.env*.example`.
- **Khi thêm biến môi trường mới** (VD task 8.1 — VNPay/Momo API key): cập
  nhật CẢ 2 nơi — (1) file `.env.example` tương ứng (root/`backend/`/`frontend/`)
  và `.env.production.example` cùng cấp nếu biến đó cần giá trị khác ở
  production, (2) bảng trong `docs/ENV_VARIABLES.md` (task 2.4.2 - tra cứu
  tổng hợp toàn bộ biến, khỏi phải lục 3 file rải rác). Bỏ qua 1 trong 2 sẽ
  lặp lại đúng kiểu lệch đã gặp ở `docs/KNOWN_TODOS.md` #6/#7/#8.
- **`get_current_user` decode JWT THẬT** (`backend/app/core/security.py`, task
  1.3.3) — verify chữ ký + hạn token bằng `JWT_SECRET_KEY`/`JWT_ALGORITHM`
  (qua dependency riêng `get_token_payload`, tách từ task 3.3.2 để
  `POST /auth/logout` tái dùng mà không phải decode token 2 lần), CHECK
  BLACKLIST qua Redis (`is_token_blacklisted`, task 3.3.2 — key
  `blacklist:jti:<jti>`, set lúc `POST /auth/logout` với TTL = thời gian còn
  lại tới lúc token hết hạn tự nhiên), rồi load đúng `User` từ MySQL theo
  `sub` trong payload, 401 nếu thiếu/sai/hết hạn/đã bị blacklist hoặc
  `is_active=False`. Redis lỗi lúc check blacklist → **fail-open** (coi như
  chưa bị blacklist, quyết định có chủ đích — Redis hiện không persist/không
  cluster, fail-closed sẽ biến Redis thành SPOF cho toàn bộ endpoint cần đăng
  nhập). `require_role(*roles)` (dependency factory dùng SAU `get_current_user`)
  check role thật của user, 403 nếu không đủ quyền. Có thể dựa vào role/
  `is_active` trả về từ đây cho logic thật.
- **Rate limit AI chat dùng Redis** — `/ai/chat` và `/ws/chat` cần giới hạn tần suất
  theo user (xem `docs/API_SPEC.md` mục 8), hiện CHƯA implement, chỉ mới khai báo
  response `429` trong docs.
- **WebSocket không xuất hiện trên Swagger UI** — giới hạn của chuẩn OpenAPI, không
  phải lỗi cấu hình.
- Route `/orders/admin` (path cố định) được đăng ký TRƯỚC `/orders/{order_id}`
  trong `app/routers/order.py` — nếu thêm route mới có path cố định xen giữa các
  route templated, giữ đúng thứ tự này để tránh bị route templated nuốt mất.
- **`frontend/Dockerfile.prod` cần `NEXT_PUBLIC_API_URL` qua `--build-arg` lúc
  `docker build`, KHÔNG PHẢI lúc `docker run`** (task 2.2.2) — đã tự kiểm chứng:
  đổi biến này lúc `docker run -e ...` không có tác dụng gì, giá trị lúc build
  đã bị nhúng cứng vào file JS tĩnh trong `.next/static/`. Hệ quả cho task 7.5.2
  (Deploy Frontend): đổi API URL giữa các môi trường (staging/production) bắt
  buộc phải build lại image tương ứng, không thể dùng chung 1 image cho nhiều
  môi trường như Backend (chỉ cần đổi `--env-file`/biến môi trường lúc chạy).
- **Upload ảnh sản phẩm (task 3.4.1) lưu LOCAL** (`app/core/storage.py`, thư mục
  `uploads/`, serve qua `StaticFiles` mount ở `/api/v1/uploads`) — dev có bind
  mount nên persist thật trên host, nhưng `Dockerfile.prod` KHÔNG có bind mount
  nên file MẤT khi container recreate — PHẢI chuyển cloud storage (S3/Cloudinary)
  trước khi deploy thật, xem `docs/KNOWN_TODOS.md` #16.
- **`POST /orders` dùng `SELECT ... FOR UPDATE` thật** (task 3.4.2/8.2 —
  `app/services/order_service.py:checkout()`) — khóa từng sản phẩm trong giỏ
  theo thứ tự `product_id` TĂNG DẦN (tránh deadlock giữa 2 giao dịch checkout
  đồng thời trùng sản phẩm) + khóa `cart_items` của chính user trước (chặn
  double-submit). `PUT /orders/{id}/status` (Admin) chỉ chấp nhận transition
  hợp lệ theo `VALID_STATUS_TRANSITIONS` (state machine cơ bản, cùng file) —
  400 nếu sai quy tắc, không âm thầm chấp nhận mọi giá trị.
