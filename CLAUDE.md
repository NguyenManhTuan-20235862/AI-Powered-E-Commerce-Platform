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

Danh sách thư viện thật: xem `backend/requirements-{core,ai,test,prod}.txt`
và `frontend/package.json` — không có gì ngoài các file này đang thực sự
được dùng trong code.

**Vì sao Backend tách 4 file requirements** (quyết định kiến trúc, không tự
đọc code suy ra được):
- `requirements-core.txt` — cài mặc định, kể cả `Dockerfile.dev` VÀ `.prod`.
- `requirements-ai.txt` — CHƯA cài mặc định (LangChain + langchain-openai),
  vì CHƯA có code tích hợp AI Agent nào trong `app/`; cài kèm khi vào task 6.x.
- `requirements-test.txt` — cài trong `Dockerfile.dev`, KHÔNG cài `.prod`
  (task 2.1.2) — production không cần test framework lúc chạy thật.
- `requirements-prod.txt` — CHỈ cài trong `Dockerfile.prod` (Gunicorn, task
  2.1.2) — dev dùng `uvicorn --reload` trực tiếp, không cần Gunicorn.

**Frontend** — lưu ý riêng ngoài danh sách package: Vitest + RTL (task 4.2.3,
`npm test`) test CHẠY ĐỘC LẬP (jsdom, mock `next/navigation`), không cần dev
server/browser thật — khác cách verify Frontend trước giờ (browser automation
thủ công, vẫn dùng song song cho UI/luồng thật), dùng cho case assert
re-render khó kiểm bằng mắt (VD `ProductFilters.test.tsx`). sonner (task
4.3.1) — toast feedback (`<Toaster />` ở `app/layout.tsx` gốc), thư viện toast
DUY NHẤT trong dự án — không viết component riêng, không thêm thư viện thứ 2.

**Chưa có trong repo**: `Makefile`, CI config, linter/formatter Backend (không
ruff/black). Frontend chỉ 1 file test (`ProductFilters.test.tsx`) — chưa phải
coverage toàn bộ component.

`docker-compose.yml` (task 2.3.1→2.3.4+3.5.2) đủ 6 service (mysql, mongodb,
redis, backend, frontend, product-sync-scheduler) — `docker compose up` chạy
TOÀN BỘ stack 1 lệnh (xem Commands). Vẫn CHƯA có compose riêng cho production
(Dockerfile.prod Backend/Frontend chưa dùng ở đâu — việc deploy sau này).

**`product-sync-scheduler`** (task 3.5.2, `run_scheduler.py`) — tiến trình
APScheduler ĐỘC LẬP, không chung process với `backend` (Gunicorn/API), dùng
lại NGUYÊN Dockerfile.dev/prod của Backend (chỉ đổi `command:` thành
`python -m scripts.run_scheduler`), chạy `sync_products_to_mongo()` theo cron
`PRODUCT_SYNC_CRON` (mặc định `0 2 * * *`, giờ VN). Tách container riêng để
tránh N Gunicorn worker mỗi worker tự chạy 1 lịch riêng (sync trùng N lần) —
luôn ĐÚNG 1 tiến trình chạy scheduler bất kể `backend` bao nhiêu worker. Lỗi
lúc sync chỉ log, KHÔNG crash scheduler. Chạy tay: `docker compose exec
product-sync-scheduler python -m scripts.sync_products_to_mongo` — CỐ TÌNH
không có endpoint HTTP, xem docstring `run_scheduler.py`.

`nginx/nginx.conf` (task 2.4.1) — routing `/` → `frontend:3000`, `/api/` →
`backend:8000` (giữ nguyên path, KHÔNG strip `/api`, khớp `API_PREFIX =
"/api/v1"` gắn cứng trong `main.py`, áp dụng cả `/ws/chat`/
`/notifications/*/stream` — path thật là `/api/v1/ws/chat`, không phải
`/ws/chat` trơ). **CHƯA đưa nginx vào `docker-compose.yml`** (có chủ đích,
xem `docs/KNOWN_TODOS.md`) — dev vẫn truy cập trực tiếp `:3000`/`:8000`,
`nginx.conf` chỉ test độc lập bằng container tạm (xem Commands).

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
npm test        # vitest run (task 4.2.3) - test chạy trong process Node, KHÔNG
                 # cần dev server đang chạy
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

Cấu trúc thư mục `backend/app/` và `frontend/app/` — xem trực tiếp cấu trúc
thư mục, chuẩn layer (core/routers/models/schemas/services) và route-group
(App Router) thông thường, khớp `docs/API_SPEC.md`. Các điểm KHÔNG tự đọc
code suy ra được (quyết định/gap phát sinh) liệt kê dưới đây:

- Backend: category service CHỈ `list_categories()` thật (task 4.2.1, phục
  vụ filter trang catalog) — CRUD category (POST/PUT/DELETE) vẫn placeholder;
  dashboard/payment vẫn placeholder (chưa tới task tương ứng).
- Frontend: `app/admin/` là segment THẬT (không phải route group), tránh
  trùng URL với `(customer)/products`.

`lib/axios.ts` (interceptor gắn JWT, CLIENT), `lib/api-server.ts` (fetch phía
SERVER, task 4.2.1 — xem `API_INTERNAL_URL` bên dưới), `lib/auth.ts` (token
localStorage), `hooks/useAuth.ts`, `types/` (`common.ts` — envelope
`ApiResponse`/`PaginatedResponse` chung; User/Product/Category/Cart khớp
schema Backend thật, Cart viết lại ở task 4.3.1 đóng `docs/KNOWN_TODOS.md`
#20 phần Cart; Order vẫn placeholder cũ, xem #20 phần còn lại).

**Design token** (task 4.1.1, `docs/DESIGN_TOKENS.md`) — màu/font/radius/
shadow khai báo 1 lần ở `app/globals.css` (`:root`), `tailwind.config.ts` map
thành class ngữ nghĩa (`bg-primary`, `bg-surface`...) TRỎ THẲNG biến đó, không
lặp hex. `app/(auth)/auth.css` (CSS thuần, từ task 1.3.4) giữ cách viết cũ
nhưng đọc chung biến `--color-*`/`--font-*` từ `globals.css`, không tự khai
báo `:root` riêng.

**`NEXT_PUBLIC_API_URL` luôn phải là URL trình duyệt truy cập được** (VD
`http://localhost:8000/api/v1`) — KHÔNG BAO GIỜ dùng tên service Docker hay
`host.docker.internal`. Lý do: biến `NEXT_PUBLIC_*` nhúng thẳng vào bundle JS
chạy ở trình duyệt (client-side) — hostname Docker chỉ có nghĩa trong network
namespace Docker, trình duyệt host không resolve được. Biến phía Backend
(server-side, chạy trong container) thì ngược lại, dùng được tên
service/`host.docker.internal`. Xem thêm task 2.2.1.

**`API_INTERNAL_URL` (task 4.2.1) — NGƯỢC LẠI `NEXT_PUBLIC_API_URL`** — dùng
cho fetch phía SERVER (`lib/api-server.ts:fetchApi()`) và origin ảnh
`next/image` (`lib/format.ts:resolveProductImageUrl()`, `next.config.ts`), vì
cả 2 chạy TRONG container Next.js (kể cả SSR hay khi `/_next/image` tự fetch
ảnh gốc ở server cho trang CSR) → phải dùng tên service Docker
(`http://backend:8000/api/v1`). Nhầm 2 biến cho nhau (NEXT_PUBLIC ở Server
Component, hoặc ngược lại ở Client Component) → lỗi kết nối, đã tự gặp cả 2
chiều lúc verify task 4.2.1.

`components/product/` (task 4.2.1): `ProductCard`/`ProductGrid` (Server
Component), `ProductFilters`/`SortDropdown` (Client Component, đổi URL
`searchParams` — filter/sort/trang nằm trên URL để share link/back-forward
hoạt động đúng).

`ProductFilters` (task 4.2.3) thêm search (debounce 450ms, tự điều hướng) +
nút "Xóa bộ lọc". QUAN TRỌNG: state field (category/giá/tồn-kho/search) PHẢI
có `useEffect` resync theo `searchParams` — chỉ đọc qua
`useState(searchParams.get(...))` (initializer, 1 lần lúc mount) sẽ hiển thị
SAI khi URL đổi từ bên ngoài (back/forward), dù list sản phẩm vẫn đúng; đã tự
gặp bug này (xem `ProductFilters.test.tsx`, test đầu tiên Frontend). Loading
state dùng `useTransition` — KHÔNG dùng `app/(customer)/products/loading.tsx`
(đã tự gặp bug treo trang, xem `docs/KNOWN_TODOS.md` #21).

`app/(customer)/products/[slug]/page.tsx` (task 4.2.2) — `generateMetadata()`
động, `notFound()` khi `GET /products/{id_or_slug}` 404 (route nhận cả `id`
số lẫn `slug`, xem `product_service._id_or_slug_filter()`). `ProductGallery.tsx`
(hiện 1 ảnh, tên tổng quát để mở rộng), `ProductInfo.tsx` (Server Component),
`QuantitySelector.tsx` (Client, chỉ UI +/-, chưa nối giỏ hàng — task 4.3),
`Breadcrumb.tsx` (dùng chung). "Sản phẩm liên quan" tái dùng `ProductGrid` có
sẵn. "Đánh giá" chỉ placeholder tĩnh — `GET /products/{id}/reviews` vẫn
`501`, KHÔNG gọi API này.

**`context/CartContext.tsx`** (task 4.3.1) — state giỏ hàng dùng chung qua
React Context (không phải hook fetch riêng lẻ), vì Header/ProductCard/
ProductInfo cần cùng trạng thái đồng bộ ngay. `CartProvider` bọc
`app/(customer)/layout.tsx` — CHỈ route Customer, `app/admin/` không wrap
(khớp Backend chặn Admin ở `/cart`). Chỉ gọi `GET /cart` khi
`useAuth().isAuthenticated === true`.

Nguyên tắc BẮT BUỘC: mọi action (`addItem`/`updateQuantity`/`removeItem`) set
state TRỰC TIẾP từ `CartRead` Backend trả về — KHÔNG tự cộng/trừ ở client
(Backend là nguồn sự thật duy nhất cho cộng dồn số lượng + validate tồn kho,
`cart_service.py:add_item()`; tự tính lại dễ lệch nếu request bị từ chối 1
phần hoặc tồn kho đổi giữa chừng). `totalCount` (badge Header) = TỔNG
`quantity` mọi dòng, KHÔNG PHẢI `items.length`. `isAuthenticated` export lại
từ `useCart()` để `AddToCartButton`/`AddToCartSection` dùng chung, tránh gọi
`useAuth()` riêng mỗi nơi (mỗi lần tốn 1 request `GET /auth/me`, xem
`docs/KNOWN_TODOS.md` #22).

**`app/(customer)/cart/`, `checkout/`, `checkout/success/`** (task 4.3.2) —
`/cart` (Client, đọc thẳng `useCart()`) dùng `CartItemRow.tsx` (mỗi dòng tự
quản `isPending`, gọi update/remove NGAY khi bấm +/-/xóa — thiết kế Stitch
không có ô nhập số tay nên không cần debounce, chỉ disable nút lúc chờ).
`/checkout` (`CheckoutPage`) chỉ guard giỏ hàng trống + layout; form thật ở
`CheckoutForm.tsx` (react-hook-form + zod, cùng pattern Login/RegisterForm) —
pre-fill từ `useAuth().user` qua `reset()` trong `useEffect` (KHÔNG
`defaultValues` vì user thường chưa load xong lúc mount). KHÔNG có field
`payment_method` — hệ thống chỉ hỗ trợ COD, radio VNPay/Momo chỉ decorative
(disabled, badge "Sắp ra mắt"). Lỗi 409 (thiếu tồn kho) hiện thẳng message
thật từ Backend qua `lib/api-error.ts:extractApiErrorMessage()`. Sau khi đặt
thành công: gọi TƯỜNG MINH `clearCart()` (Context không tự biết `POST /orders`
đã xóa `cart_items`) rồi `router.push("/checkout/success?order_id=<id>")`.

**Route xác nhận là `/checkout/success?order_id=<id>`, KHÔNG PHẢI
`/orders/[id]/confirmation`** (có chủ đích) — đây là bước cuối nhất thời của
checkout, không phải thuộc tính bền vững của đơn hàng; đặt dưới
`/orders/[id]/...` sẽ khiến trang trông như "vừa đặt xong" mỗi lần bookmark
dù đơn có thể đã giao lâu. `/orders/[id]` hiện chỉ stub tĩnh (task 4.3.3).
`OrderConfirmation.tsx` (bọc `<Suspense>` vì dùng `useSearchParams()`) fetch
LẠI `GET /orders/{id}` (không tin data từ `POST /orders` truyền qua điều
hướng — không truyền được qua URL, và fetch lại giúp trang chịu refresh).
KHÔNG hiển thị "Dự kiến giao hàng" dù Stitch có — Backend không có field ước
tính ngày giao, không hiện ngày giả.

**`orders.shipping_name`** (task 4.3.2, thêm sau `shipping_address`/
`shipping_phone` từ task 3.1.3) — gap phát hiện lúc port Stitch: form
checkout có ô "Họ và tên" người nhận nhưng Backend chưa có cột lưu. Snapshot
lúc đặt, cùng nguyên tắc `shipping_address`/`shipping_phone` (KHÔNG tham
chiếu `users.full_name` — người nhận có thể khác chủ tài khoản). Migration
`f00f506b3a6b` đơn giản, không đụng FK/index nên không gặp vấn đề như
`docs/KNOWN_TODOS.md` #11.

**Client Component KHÔNG dùng `next/image` cho ảnh sản phẩm** (VD
`CartItemRow.tsx`, order summary trong `CheckoutForm.tsx`) — dùng `<img>` +
`lib/format.ts:resolveProductImageUrlClient()` (origin từ
`NEXT_PUBLIC_API_URL`, khác bản Server Component dùng `API_INTERNAL_URL`). Lý
do: `/_next/image` luôn fetch ảnh gốc Ở PHÍA SERVER bất kể SSR/CSR — dùng
`next/image` ở Client Component với `API_INTERNAL_URL` (server-only,
`undefined` ở browser) sẽ ra ảnh vỡ; đơn giản nhất là bỏ tối ưu ảnh Next.js
cho case này.

**`app/(customer)/orders/`** (task 4.3.3) — `page.tsx` là Client Component
(CSR), NGƯỢC LẠI catalog SSR — trang cần tương tác nhiều (đổi tab, hủy đơn,
cập nhật ngay) hơn cần SEO (trang cá nhân, luôn cần đăng nhập). Tab lọc
(`OrderStatusFilter.tsx`) vẫn dùng URL `?status=` làm nguồn sự thật (cùng
pattern `ProductFilters`) nhưng re-fetch qua `useEffect` gọi thẳng axios thay
vì Server Component tự re-render. `GET /orders` trước đó không nhận
`?status=` (chỉ `/orders/admin` có) — mở rộng ở task này, tái dùng
`order_service.list_orders()` có sẵn tham số (chỉ thiếu khai báo router).

`components/order/OrderStatusBadge.tsx` map 5 trạng thái `OrderStatus` →
màu, CHỈ dùng token có sẵn (`primary`/`secondary`/`error`): `pending`
(`primary-100`) → `confirmed` (`primary-300`) → `shipping` (`primary` đặc) →
`delivered` (`secondary` đặc) → `cancelled` (`error-container`, khớp Stitch).
Stitch chỉ minh họa 3/5 trạng thái — `confirmed`/`shipping` tự chọn theo quy
tắc trên.

`OrderCard.tsx` KHÔNG hiển thị thumbnail như Stitch (có chủ đích) —
`OrderItemRead` là snapshot BẤT BIẾN, cố tình không có field ảnh (không join
dữ liệu sản phẩm hiện tại vào đơn đã chốt, cùng nguyên tắc snapshot
`product_name`/`price_at_purchase`) — card chỉ hiện text. Nút "Hủy đơn" chỉ
hiện khi `status === "pending"`, dùng `window.confirm()` (chưa có modal
riêng, đúng quy mô đồ án) — hủy xong gọi lại `onCancelled` (cha
`fetchOrders()` lại toàn bộ, KHÔNG tự patch state cục bộ vì đơn vừa hủy có
thể không còn khớp tab đang xem).

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

- **Đọc `docs/API_SPEC.md` trước khi thêm route mới** — nguồn sự thật cho
  path/method/tag/quyền truy cập. Nếu code lệch spec, đồng bộ lại 1 trong 2
  phía, đừng để lệch âm thầm.
- **Không commit `.env` thật** — `.gitignore` (gốc repo VÀ `frontend/`, cả 2
  sửa ở task 2.4.2) chặn `.env`/`.env.*`, CHỈ cho phép `.env*.example`.
- **Khi thêm biến môi trường mới**: cập nhật CẢ 2 nơi — (1) `.env.example`
  tương ứng (root/backend/frontend) + `.env.production.example` nếu khác giá
  trị production, (2) bảng `docs/ENV_VARIABLES.md`. Bỏ qua 1 trong 2 sẽ lặp
  lại lệch đã gặp ở `docs/KNOWN_TODOS.md` #6/#7/#8.
- **`get_current_user` decode JWT THẬT** (`security.py`, task 1.3.3) — verify
  chữ ký + hạn token bằng `JWT_SECRET_KEY`/`JWT_ALGORITHM` (qua
  `get_token_payload`, tách để `POST /auth/logout` tái dùng không decode 2
  lần), CHECK BLACKLIST Redis (`is_token_blacklisted`, key
  `blacklist:jti:<jti>`, set lúc logout với TTL = thời gian còn lại), rồi load
  `User` MySQL theo `sub`; 401 nếu thiếu/sai/hết hạn/blacklist/
  `is_active=False`. Redis lỗi lúc check blacklist → fail-open (có chủ đích —
  Redis không persist/cluster, fail-closed biến Redis thành SPOF cho mọi
  endpoint cần đăng nhập). `require_role(*roles)` check role thật, 403 nếu
  không đủ quyền.
- **Rate limit AI chat dùng Redis** — `/ai/chat` và `/ws/chat` (xem
  `docs/API_SPEC.md` mục 8), hiện CHƯA implement, chỉ mới khai báo response
  `429` trong docs.
- **WebSocket không xuất hiện trên Swagger UI** — giới hạn chuẩn OpenAPI,
  không phải lỗi cấu hình.
- Route `/orders/admin` (path cố định) đăng ký TRƯỚC `/orders/{order_id}`
  trong `order.py` — route mới có path cố định xen giữa route templated phải
  giữ thứ tự này. `/products/admin` (task 4.4.1) áp dụng đúng quy tắc, đăng
  ký TRƯỚC `/products/{id_or_slug}`.
- **`frontend/Dockerfile.prod` cần `NEXT_PUBLIC_API_URL` qua `--build-arg`
  lúc `docker build`, KHÔNG PHẢI `docker run`** (task 2.2.2, đã tự kiểm chứng
  — đổi lúc `docker run -e` vô tác dụng, giá trị build đã nhúng cứng vào JS
  tĩnh). Hệ quả task 7.5.2: đổi API URL giữa môi trường bắt buộc build lại
  image, không dùng chung 1 image như Backend (chỉ cần đổi env lúc chạy).
- **Cài package Frontend mới trên HOST KHÔNG đủ để container `frontend` thấy
  được** (đã tự gặp lỗi lúc thêm `sonner` task 4.3.1: "Module not found" dù
  `package.json`/lock đã đúng) — `docker-compose.yml` mount
  `frontend_node_modules` là NAMED VOLUME riêng đè `/app/node_modules` (cố ý,
  tránh node_modules Windows đè bản Linux build image), không tự đồng bộ theo
  `npm install` trên host. Sau khi thêm package mới, PHẢI
  `docker compose exec frontend npm install` rồi
  `docker compose restart frontend` — bỏ qua sẽ mất thời gian debug lại lỗi
  này.
- **Upload ảnh sản phẩm (task 3.4.1) lưu LOCAL** (`storage.py`, thư mục
  `uploads/`, serve qua `StaticFiles` ở `/api/v1/uploads`) — dev persist thật
  qua bind mount, nhưng `Dockerfile.prod` KHÔNG có bind mount nên file MẤT
  khi container recreate — PHẢI chuyển cloud storage (S3/Cloudinary) trước
  khi deploy thật, xem `docs/KNOWN_TODOS.md` #16.
- **`POST /orders` dùng `SELECT ... FOR UPDATE` thật** (task 3.4.2/8.2,
  `order_service.py:checkout()`) — khóa từng sản phẩm trong giỏ theo
  `product_id` TĂNG DẦN (tránh deadlock giữa 2 checkout đồng thời) + khóa
  `cart_items` của user trước (chặn double-submit). `PUT /orders/{id}/status`
  (Admin) chỉ chấp nhận transition hợp lệ theo `VALID_STATUS_TRANSITIONS` —
  400 nếu sai, không âm thầm chấp nhận mọi giá trị.
