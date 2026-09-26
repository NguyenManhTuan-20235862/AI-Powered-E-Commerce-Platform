# AGENTS.md

Hướng dẫn cho Codex khi làm việc trong repo này.

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
- `requirements-ai.txt` — LangChain + `langchain-openai`, đã cài trong CẢ
  `Dockerfile.dev` và `Dockerfile.prod` từ task 6.1 vì `/ws/chat` hiện gọi và
  stream LLM thật. Vẫn tách file để dependency AI có ranh giới rõ với core.
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
ruff/black). Frontend đã có Vitest cho filters/pagination, cart/checkout,
Admin components và hooks realtime (`useChatSocket`, `useOrderStatusStream`),
nhưng vẫn chưa phải coverage toàn bộ component/page.

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
pip install -r requirements-core.txt -r requirements-ai.txt -r requirements-test.txt
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

**Quản trị sản phẩm, danh mục và kho** (task "Hoàn thiện quản trị sản phẩm,
danh mục và kho") — hoàn thiện thêm cho các module đã có sẵn từ trước (CRUD
Product/Category task 3.4.1/4.4.1, Inventory Admin), KHÔNG phải tính năng
mới:

- **Upload ảnh sản phẩm** (`app/core/storage.py`) - validate THÊM bằng magic
  byte đọc từ NỘI DUNG file thật (`_sniff_image_extension()`: JPEG/PNG/GIF/WEBP),
  không còn chỉ tin `Content-Type` header (client tự khai, không được trình
  duyệt validate nội dung - 1 file bất kỳ hoàn toàn có thể gửi kèm
  `Content-Type: image/png` giả). Extension file lưu trên đĩa lấy từ kết quả
  SNIFF được, không phải suy từ `Content-Type`. **Ảnh CŨ tự xóa khi upload ảnh
  MỚI** (`delete_product_image()`, đóng `docs/KNOWN_TODOS.md` #18) - router gọi
  hàm này NGAY SAU khi ảnh mới đã lưu + `db.commit()` thành công (không phải
  trước) để không mất ảnh cũ nếu bước lưu ảnh mới thất bại giữa chừng; chỉ xóa
  nếu `image_url` do chính `save_product_image()` tạo ra (validate path nằm
  trong `UPLOAD_ROOT`), bỏ qua im lặng cho seed data/URL ngoài.
- **`GET /products/admin` thêm `?product_id=`** (bên cạnh `?is_active=` đã có
  từ task 4.4.1) - lọc CHÍNH XÁC đúng 1 sản phẩm (kể cả đã ẩn), dùng cho link
  "tới sản phẩm" từ trang lịch sử kho. `app/admin/products/page.tsx` (vốn CHỦ
  Ý không đồng bộ filter qua URL, xem đoạn cũ bên dưới) có NGOẠI LỆ DUY NHẤT:
  đọc `?product_id=` MỘT CHIỀU lúc mount (không ghi ngược lại URL sau đó) -
  cần bọc `<Suspense>` vì dùng `useSearchParams()`. Hiện banner "Đang lọc theo
  đúng 1 sản phẩm" kèm nút "Bỏ lọc" khi filter này đang áp dụng.
- **`ProductTable.tsx`** (Admin) thêm select filter "Trạng thái" (`is_active`
  - Backend đã hỗ trợ sẵn, chỉ thiếu UI) cạnh filter category có sẵn. Cột
  "Trạng thái" thêm badge "Hết hàng" (viền đỏ, KHÁC hẳn badge "Đã ẩn" nền đỏ
  đặc để không lẫn 2 khái niệm) khi `stock_quantity === 0` - ĐỘC LẬP với
  `is_active` (1 sản phẩm có thể vừa hết hàng vừa vẫn đang bán).
- **Lịch sử điều chỉnh kho** (`/admin/inventory`, tab "Lịch sử điều chỉnh"):
  cột "Admin" đổi từ `#admin_id` trơ sang TÊN thật (`admin_name`) - JOIN
  BATCH sang `users` ở `inventory_service.list_adjustments()` (KHÔNG
  denormalize lúc ghi như `product_name`, KHÔNG thêm cột/migration - cùng
  pattern `ReviewAdminRead.product_name`, task review sản phẩm). Cột "Sản
  phẩm" (cả tab lịch sử LẪN "Sắp hết hàng") giờ là link tới
  `/admin/products?product_id=<id>`. Thêm nút "Xuất CSV" (chỉ hiện ở tab lịch
  sử) - fetch HẾT các trang khớp filter hiện tại (KHÔNG chỉ 20 dòng trang
  đang xem, giới hạn an toàn 500 trang), kèm BOM UTF-8 để Excel đọc đúng
  tiếng Việt có dấu.
- **Cây danh mục** (`CategoryTable.tsx`/`CategoryFormModal.tsx`) - validate
  vòng lặp/chặn xóa danh mục còn sản phẩm hoặc danh mục con đã đầy đủ THẬT từ
  trước (`category_service.would_create_cycle()`/`count_products_in_category()`/
  `count_child_categories()`, xem docstring `category_service.py` - KHÔNG cần
  sửa gì thêm ở Backend). Chỉ CÁCH HIỂN THỊ Frontend cần cải thiện: bản cũ
  sort alphabet + chỉ hiện tên cha TRỰC TIẾP khiến cây sâu ≥ 3 cấp mất ngữ
  cảnh ông/cụ. `lib/category-tree.ts:buildCategoryTreeOrder()` (dùng chung 2
  component) dựng lại thứ tự CÂY thật (cha luôn đứng trước con, thụt lề) +
  breadcrumb ĐẦY ĐỦ tổ tiên (VD "Điện tử > Điện thoại") cho `CategoryTable.tsx`,
  và nhãn thụt lề cho dropdown "Danh mục cha" của `CategoryFormModal.tsx`.

**Quản lý người dùng Admin** (`/admin/users`, hoàn thiện thêm ở task "Hoàn
thiện quản lý tài khoản Admin") — `UserTable.tsx` ẩn nút "Khóa"/"Mở khóa" ở
hàng `role === "admin"` (chỉ hiện "—"), khớp ĐÚNG giới hạn Backend thật:
`PUT /users/{id}/status` trả 403 nếu target là BẤT KỲ Admin nào (kể cả tự
khóa chính mình, xem `app/routers/user.py`) — UI ẩn trước để tránh 1 request
403 vô ích, không phải giới hạn UI đơn thuần như quyết định ban đầu.

`UserDetailModal.tsx` (modal, KHÔNG phải route `/admin/users/[id]` riêng —
Admin panel chưa có tiền lệ route chi tiết nào, Product/Category đều sửa qua
modal) — nút "Chi tiết" hiện cho MỌI role (kể cả Admin, chỉ hành động KHÓA
mới bị chặn), fetch LẠI `GET /users/{id}` khi mở (cho endpoint này — trước
đó Frontend hoàn toàn không gọi dù đã có sẵn ở Backend/`docs/API_SPEC.md` —
một mục đích sử dụng thật, không tin dữ liệu dòng bảng có thể đã cũ) + hiện
lịch sử đơn hàng qua `GET /orders/admin?user_id=<id>` (tham số `user_id` mới
thêm ở router — `order_service.list_orders()` vốn đã hỗ trợ sẵn tham số này
từ trước, chỉ Customer dùng qua `GET /orders`, router Admin trước đó hardcode
`user_id=None`).

Khóa/mở khóa xong (`UserTable.tsx:handleToggleActive`) KHÔNG gọi lại
`fetchUsers()` toàn bảng — `onChanged` nhận thẳng `AdminUser` mới nhất từ
response `PUT` (đã có sẵn, trước đây bỏ qua chỉ đọc `message`), `page.tsx`
patch ĐÚNG 1 dòng qua `setUsers(prev => prev.map(...))`. Đánh đổi đã chấp
nhận: nếu đang lọc theo `isActive` và dòng vừa đổi không còn khớp bộ lọc,
dòng đó vẫn hiện tạm (không tự biến mất) tới lần fetch tự nhiên kế tiếp (đổi
trang/filter/tìm kiếm) — đơn giản hơn hẳn so với tự đồng bộ lại
`total`/`totalPages` cho 1 tình huống không thường xuyên, cùng tinh thần "nếu
hợp lý" đã yêu cầu.

Cấu trúc thư mục `backend/app/` và `frontend/app/` — xem trực tiếp cấu trúc
thư mục, chuẩn layer (core/routers/models/schemas/services) và route-group
(App Router) thông thường, khớp `docs/API_SPEC.md`. Các điểm KHÔNG tự đọc
code suy ra được (quyết định/gap phát sinh) liệt kê dưới đây:

- Backend: category service có CRUD ĐẦY ĐỦ thật (`POST`/`PUT`/`DELETE
  /categories/{id}`, thêm sau task 4.2.1 vốn chỉ có `list_categories()` -
  xem đoạn riêng "Quản trị danh mục" bên dưới cho chi tiết validate/xóa);
  payment vẫn placeholder (chưa tới task tương ứng).
- Frontend: `app/admin/` là segment THẬT (không phải route group), tránh
  trùng URL với `(customer)/products`.

**`GET /admin/dashboard/{summary,revenue,top-products}`** (task 5.3.1,
`app/services/dashboard_service.py`) — "realtime" trong tên task 5.3 CHỈ có
nghĩa Admin fetch số liệu mới nhất lúc mở trang/bấm refresh, KHÔNG đẩy qua
SSE/WebSocket (đã xác nhận trước khi code — dữ liệu tổng hợp, không phải 1
sự kiện đơn lẻ như trạng thái đơn hàng ở 5.1/5.2). Quyết định nghiệp vụ quan
trọng: **doanh thu loại trừ CHỈ đơn `cancelled`** (tính cả
`pending`/`confirmed`/`shipping`/`delivered`) — nhưng **`total_orders` đếm
CẢ đơn `cancelled`** (chỉ số hoạt động, khác doanh thu, xem
`REVENUE_ELIGIBLE_STATUSES` so với query đếm `total_orders`). `new_users`
CHỈ đếm `role=customer` (loại `admin`). Mặc định 30 ngày gần nhất nếu không
truyền `date_from`/`date_to`. `revenue` trả mảng LIÊN TỤC (điền 0 cho
ngày/tuần/tháng không phát sinh đơn — cần cho Chart.js không bị "nhảy cóc"
trục thời gian). `top-products` mặc định sắp theo SỐ LƯỢNG bán
(`sort_by=quantity`, đổi được sang `revenue`) — nhóm theo `product_id`,
`name` trả về là tên HIỆN TẠI join bảng `products` (KHÔNG dùng snapshot
`order_items.product_name` — hợp lý hơn cho báo cáo Admin xem đúng sản phẩm
đang bán, khác nguyên tắc snapshot bất biến dùng cho hóa đơn). Cache Redis
qua `get_or_set_cache` có sẵn, TTL 300s (5 phút) — **KHÔNG active-invalidate**
khi đơn hàng đổi trạng thái (khác `product_service.py` cho CRUD sản phẩm) -
đã xác nhận dữ liệu thống kê không cần tức thời, chấp nhận độ trễ tới 5 phút.

**Quản trị dashboard và realtime Admin** (task "Hoàn thiện dashboard và
realtime Admin") — hoàn thiện thêm cho dashboard đã có (task 5.3.1/5.3.2),
**GIỮ NGUYÊN** quyết định "fetch khi mở trang/bấm làm mới" ở trên (xác nhận
lại, không đổi):

- **Validate `date_from <= date_to`** (`dashboard_service.resolve_date_range()`,
  400 nếu sai) — trước đây thiếu bước này, khoảng ngày đảo ngược không lỗi rõ
  ràng mà âm thầm trả kết quả RỖNG (mọi filter `created_at >= date_from AND
  created_at < date_to + 1 ngày` luôn `False`), dễ hiểu lầm "không có dữ
  liệu". Validate ĐÚNG 1 chỗ (hàm dùng chung cho cả 3 endpoint), không lặp
  lại ở từng router.
- **`app/admin/dashboard/page.tsx`** — bộ chọn khoảng ngày THẬT (2 input
  `type="date"`, thay nút "Khoảng ngày" decorative/disabled cũ) + bộ chọn
  interval Ngày/Tuần/Tháng cho biểu đồ doanh thu (trước đó hardcode `"day"`,
  Backend đã hỗ trợ `interval` từ task 5.3.1, chỉ thiếu UI). Đổi khoảng
  ngày/interval refetch CẢ 3 API cùng lúc (kể cả khi chỉ đổi interval, vốn
  chỉ ảnh hưởng `/revenue`) — chấp nhận 2 lệnh gọi dư cho `summary`/
  `top-products` vì Backend đã cache Redis (TTL 5 phút, cùng tham số) —
  không đáng tách riêng 2 effect cho quy mô đồ án. Input ngày mặc định RỖNG,
  tự điền lại bằng khoảng THẬT Backend áp dụng (`summary.date_from`/`date_to`)
  sau lần fetch đầu — CHỈ 1 LẦN (guard qua `useRef`, không phải state, tránh
  vòng lặp effect). Validate `date_from <= date_to` CẢ 2 phía (Frontend chặn
  trước khi gọi API + Backend vẫn tự validate lại làm tuyến phòng thủ cuối).
- **Tách rõ trạng thái LỖI (`loadError`) khỏi trạng thái RỖNG THẬT** (cùng
  pattern `OrdersView.tsx`) — trước đây lỗi fetch (`Promise.all` reject) chỉ
  hiện toast rồi rơi vào giao diện trông giống "chưa có dữ liệu" (KPI hiện
  "-", biểu đồ hiện "Chưa có dữ liệu..."), Admin không phân biệt được "API
  lỗi" với "khoảng ngày này thật sự không có đơn nào" — giờ lỗi hiện khối
  riêng + nút "Thử lại", KHÔNG lẫn với thông báo rỗng của từng chart.
- **`GET /notifications/admin/stream` CHÍNH THỨC LOẠI KHỎI PHẠM VI** (trước
  đó chỉ là `501` placeholder từ task 5.2.1, đã XÓA HẲN route, cập nhật
  `docs/API_SPEC.md`) — quyết định: toàn bộ Admin panel (đơn hàng/kho/sản
  phẩm/dashboard) nhất quán dùng mô hình fetch-khi-mở-trang/bấm-làm-mới,
  KHÔNG có mặt SSE/WebSocket nào khác ở phía Admin (khác Customer, có SSE
  `/notifications/orders/stream` phục vụ 1 nhu cầu hẹp: user đang xem trang
  đơn hàng CỦA CHÍNH MÌNH). Thêm 1 kênh realtime riêng chỉ để báo "có đơn
  mới" sẽ là bề mặt UI/hạ tầng MỚI DUY NHẤT không nhất quán với phần còn lại
  (cần thêm: publish event lúc `POST /orders` tạo đơn thành công — hiện
  `notification_service.py` chỉ publish lúc đổi TRẠNG THÁI đơn qua `PUT
  /orders/{id}/status`, KHÔNG phải lúc TẠO đơn; + 1 bề mặt UI mới hoàn toàn
  trong Admin layout, VD chuông thông báo — chưa tồn tại), trong khi chưa có
  nhu cầu thật nào vượt quá "Admin bấm làm mới khi cần xem đơn mới" ở quy mô
  đồ án hiện tại — không giữ `501` vô thời hạn, quyết định dứt điểm thay vì
  để treo.

**Dọn frontend để không còn màn hình giả** (task "Dọn frontend để không còn
màn hình giả") — nguyên tắc áp dụng xuyên suốt: KHÔNG còn nút/link nhìn như
dùng được nhưng thực tế không có hành vi (implement thật, hoặc bỏ hẳn, không
giữ placeholder vô thời hạn):

- **`/chat` (route trang riêng) ĐÃ XÓA** - trước đó chỉ là stub tĩnh "sẽ
  triển khai sau" (`app/(customer)/chat/page.tsx`), nhưng `ChatWidget.tsx`
  (nút nổi, task 5.1.2) đã là chat AI THẬT từ lâu (`/ws/chat` stream LLM thật
  từ task 6.1.1-6.1.2, xem đoạn "Streaming AI `/ws/chat`" bên dưới) - hiện
  sẵn trên MỌI trang Customer đã đăng nhập (`app/(customer)/layout.tsx`).
  Giữ 1 route `/chat` trỏ tới trang tĩnh trùng lặp, kém hơn hẳn widget thật
  là đúng loại "màn hình giả" cần dọn - bỏ nav item "Chat AI" khỏi CẢ
  `Header.tsx` LẪN `Footer.tsx` (2 nơi, không chỉ 1), không cần "chuyển
  hướng" vì widget vốn đã nổi sẵn không cần link.
- **"Quên mật khẩu?" (`LoginForm.tsx`) ĐÃ BỎ** - trước đó `href="#"` +
  `preventDefault()`, KHÔNG có hành vi gì. Quyết định: BỎ hẳn (không implement
  thật) - dự án CHƯA có hạ tầng gửi email nào (không SMTP, không service như
  SendGrid, không bảng lưu token reset) - xây tính năng reset mật khẩu qua
  email cho ĐÚNG 1 link trong 1 task "dọn dẹp UI giả" không tương xứng, đây
  là đầu tư hạ tầng mới hoàn toàn chứ không phải dọn dẹp.
- **Thống nhất xử lý 401 vào ĐÚNG 1 NƠI** (`lib/axios.ts`, interceptor response
  đã có sẵn từ trước - KHÔNG viết lại từ đầu) - trước đó `OrderDetailView.tsx`
  tự có nhánh xử lý 401 RIÊNG (`router.replace("/login")`) chạy SONG SONG,
  ĐUA với chính điều hướng `window.location.href` của interceptor cho CÙNG 1
  lỗi 401 - 2 cơ chế redirect cùng lúc. `redirectToLogin()` giờ điều hướng
  `/login?session_expired=1` (banner giải thích LÝ DO, `LoginForm.tsx` đọc
  param này - cùng pattern `?registered=1` đã có) VÀ - quan trọng hơn - khi
  ĐÃ chắc chắn điều hướng (không refresh được, hoặc thiếu refresh token, và
  KHÔNG đánh dấu `skipAuthRedirect`), promise trả về `abandon()` (KHÔNG BAO
  GIỜ resolve/reject) thay vì `Promise.reject(error)` - lý do: hàng chục
  component khắp app CHỈ generic `catch` + `toast.error(extractApiErrorMessage(...))`
  cho MỌI loại lỗi (không riêng 401) - nếu vẫn reject bình thường, TẤT CẢ
  những nơi đó sẽ NHÁY 1 thông báo lỗi sai ngữ cảnh ("Không tải được sản
  phẩm"...) đúng lúc trang đang điều hướng đi - "bỏ rơi" promise ở ĐÚNG 1 chỗ
  (interceptor) khiến MỌI component tự động im lặng chờ điều hướng, không
  cần sửa từng nơi riêng lẻ. `OrderDetailView.tsx` bỏ hẳn nhánh 401 riêng (dead
  code sau thay đổi này - promise không bao giờ reject cho case đó nữa).
  `skipAuthRedirect: true` (dùng cho `GET /auth/me`/`POST /auth/logout` NỀN
  lúc `AuthProvider` mount) KHÔNG bị ảnh hưởng - vẫn reject bình thường như cũ.
- **Thêm `app/not-found.tsx` + `app/error.tsx` + `app/global-error.tsx`**
  (trước đây KHÔNG có file nào trong 3 file này - Next.js tự hiện trang lỗi
  mặc định, trắng, không theo design token) - `not-found.tsx`/`error.tsx`
  render BÊN TRONG `RootLayout` như 1 page thường (dùng chung design token/
  Tailwind class được). `global-error.tsx` CHỈ kích hoạt khi CHÍNH
  `RootLayout` throw (hiếm) - PHẢI tự khai lại `<html>`/`<body>` (Next.js quy
  định, thay thế hẳn layout gốc lúc đó) - cố tình viết ĐƠN GIẢN NHẤT (CSS
  inline, không import font/Provider nào) vì chính những thứ đó có thể là
  nguyên nhân gây lỗi tầng layout gốc.
- **`Sidebar.tsx` (Admin) - sửa nốt bug `bg-foreground/40`** (đóng
  `docs/KNOWN_TODOS.md` #24, cùng loại lỗi + cách sửa đã áp dụng cho
  `ProductFilters.tsx`/`ProductFormModal.tsx` trước đó) - đổi sang
  `bg-black/40`, overlay drawer mobile Admin giờ tối thật thay vì trong suốt
  hoàn toàn (Tailwind không áp được opacity modifier lên `foreground.DEFAULT`
  vì đây là CSS custom property trần, không phải giá trị màu tĩnh).
- **VNPay/Momo (`CheckoutForm.tsx`) - RÀ SOÁT LẠI lúc task này, GIỮ NGUYÊN
  decorative** (không phải "màn hình giả" cần dọn) - radio đã `disabled`
  thật (không có state/onChange giả), `cursor-not-allowed` + `opacity-60
  grayscale` + badge "Sắp ra mắt" rõ ràng, KHÔNG bọc trong `<label>` nên bấm
  vào chữ cũng không có hành vi gì - khác hẳn 1 link/nút trông bấm được
  nhưng im lặng không làm gì. **CẬP NHẬT ở task "Quyết định và hoàn thiện
  thanh toán" (sau task này)**: VNPay đã chuyển từ decorative sang CHỨC NĂNG
  THẬT - CHỈ riêng Momo còn giữ nguyên dạng disabled/"Sắp ra mắt" như mô tả
  ở trên, xem đoạn riêng bên dưới.

**Quyết định và hoàn thiện thanh toán** (task "Quyết định và hoàn thiện
thanh toán") — quyết định đã xác nhận: triển khai VNPay sandbox THẬT (không
chỉ COD), CHỈ VNPay (KHÔNG làm đồng thời Momo - "hoàn thiện 1 cổng tốt có
giá trị hơn 2 cổng dở dang"). Thay 3 endpoint `501` cũ (task 8.1) bằng
`app/services/payment_service.py`/`app/routers/payment.py` thật. Chi tiết
thiết kế/lý do đầy đủ nằm trong docstring `payment_service.py` (rất dài, chỉ
tóm tắt các điểm KHÔNG tự đọc code suy ra được ở đây):

- **`POST /orders` (`order_service.checkout()`) GIỮ NGUYÊN HOÀN TOÀN** -
  KHÔNG có field `payment_method`, luôn tạo `Order` + trừ tồn kho ngay lập
  tức bất kể phương thức thanh toán (như trước giờ). VNPay là bước THỨ HAI,
  xảy ra SAU khi `Order` đã tồn tại (`POST /payments/create` nhận
  `order_id`) - khớp ĐÚNG quan hệ 1-1 `payments.order_id` đã thiết kế sẵn
  trong DBML/model từ đầu dự án (KHÔNG cần migration mới). Quyết định CÓ CHỦ
  ĐÍCH: dựng lại checkout thành "giữ chỗ trước, thanh toán rồi mới tạo đơn
  thật" là thay đổi kiến trúc LỚN vào 1 luồng transaction đã ổn định/test kỹ
  (`SELECT ... FOR UPDATE`, khóa chống deadlock) - không tương xứng phạm vi
  "hoàn thiện thanh toán". Hệ quả chấp nhận: đơn "pending" vẫn giữ tồn kho
  đã trừ dù Customer bỏ dở thanh toán VNPay - giống hệt rủi ro COD sẵn có,
  Admin xử lý bằng `PUT /orders/{id}/cancel` có sẵn (tự hoàn kho).
- **`PUT /orders/{id}/status` KHÔNG gate theo `Payment.status`** - Admin vẫn
  tự do xác nhận/giao đơn dù VNPay CHƯA `success` (quyết định CÓ CHỦ ĐÍCH,
  không phải thiếu sót) - kiểm tra đã thanh toán hay chưa là trách nhiệm
  NGHIỆP VỤ của Admin (xem trạng thái ở chi tiết đơn), không tự động khóa
  cứng `order_service.VALID_STATUS_TRANSITIONS` đã test kỹ - ngoài phạm vi
  task này.
- **Callback (`GET /payments/callback`) - xác minh chữ ký HMAC-SHA512 +
  đối chiếu `vnp_Amount` với `Payment.amount` ĐÃ LƯU SẴN** (KHÔNG tin số
  tiền/trạng thái do callback tự khai, kể cả sau khi chữ ký đúng - phòng thủ
  2 lớp) - idempotent thật (`with_for_update()` + chỉ chuyển status khi đang
  "pending", gọi lại nhiều lần cho CÙNG giao dịch không xử lý lại/không ghi
  đè `transaction_id` lần 2). `vnp_TxnRef` = `Payment.id` (không sinh mã
  riêng). Đây là target CỦA `vnp_ReturnUrl` (trình duyệt KHÁCH tự điều
  hướng tới sau khi thanh toán ở VNPay) - response là REDIRECT (303) sang
  Frontend `/checkout/payment-result?order_id=<id>&status=success|failed`
  (hoặc `status=invalid` nếu không xác minh được), KHÔNG PHẢI JSON kiểu IPN
  chuẩn VNPay - đơn giản hóa CÓ CHỦ ĐÍCH cho quy mô đồ án (`docs/API_SPEC.md`
  mục 6 chỉ đặc tả ĐÚNG 1 endpoint callback, không tách riêng IPN server-to-
  server - deploy thật sau này nên cấu hình thêm IPN URL riêng trên merchant
  portal VNPay để có thêm 1 lớp xác nhận không phụ thuộc trình duyệt khách
  quay lại, xem `docs/KNOWN_TODOS.md`).
- **Retry thanh toán DÙNG LẠI ĐÚNG 1 dòng `Payment`** (KHÔNG tạo dòng mới -
  `payments.order_id` UNIQUE thật theo DBML, không phải giới hạn tự đặt) -
  "pending" cho tạo lại URL mới (link VNPay cũ có thể hết hạn ~15 phút),
  "failed" reset về "pending" rồi tạo lại, "success"/"refunded" -> 409 (từ
  chối). `OrderDetailView.tsx` có nút "Thanh toán lại qua VNPay" khi
  `payment.status` đang "pending"/"failed" - gọi lại `POST /payments/create`
  rồi điều hướng CỨNG (`window.location.href`, KHÔNG PHẢI `router.push` -
  `payment_url` là domain NGOÀI app).
- **`CheckoutForm.tsx`**: `paymentMethod` là state THUẦN FRONTEND (KHÔNG gửi
  trong `POST /orders`). Chọn VNPay + submit: tạo `Order` trước (y hệt COD),
  RỒI gọi `POST /payments/create`, RỒI điều hướng cứng sang `payment_url`.
  Nếu bước tạo giao dịch VNPay THẤT BẠI (VD 503 chưa cấu hình
  `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET`) - Đơn ĐÃ tạo thành công thật, KHÔNG
  hiện "đặt hàng thất bại" (sai sự thật) - toast lỗi riêng rồi VẪN đưa khách
  sang `/checkout/success` (fallback COD-style, khách thanh toán lại VNPay
  sau từ chi tiết đơn) - đã tự verify thật qua browser (503 do chưa cấu hình
  ở môi trường dev mặc định).
- **`/checkout/payment-result`** (trang MỚI, đúng yêu cầu "trang kết quả
  thanh toán") - `?order_id=`/`?status=` trên URL CHỈ dùng cho nhãn "lạc
  quan" lúc đang fetch - LUÔN fetch LẠI `GET /payments/{orderId}/status`
  (nguồn sự thật DUY NHẤT) trước khi hiện kết quả CUỐI CÙNG, KHÔNG tin thẳng
  query param (cùng nguyên tắc `OrderConfirmation.tsx`).
- **Đã tự verify THẬT end-to-end** (không chỉ qua pytest) bằng cách tạm thời
  set `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` giả trong `backend/.env` (XÓA
  ngay sau khi xong, không phải giá trị sandbox thật) - xác nhận: URL
  redirect ký đúng thật sự điều hướng được tới `sandbox.vnpayment.vn` (VNPay
  từ chối vì mã merchant giả - đúng dự kiến, chứng minh cấu trúc request
  đúng chuẩn); callback ký tay bằng Node.js (thuật toán HMAC-SHA512 độc lập)
  verify khớp phía Backend Python - xác nhận encode `application/
  x-www-form-urlencoded` (`quote_plus`, dấu cách -> "+") nhất quán 2 chiều;
  retry dùng lại đúng 1 `Payment.id`; `OrderDetailView`/`PaymentResult` hiện
  đúng dữ liệu thật cho cả 3 trạng thái (success/failed/pending sau retry).
  **CHƯA verify được với credential sandbox VNPay THẬT** (cần bạn tự đăng ký
  tại sandbox.vnpayment.vn) - đây là giới hạn đã biết trước, không phải bỏ
  sót.

**Chốt các trường hợp lỗi và retry của thanh toán** (task cùng tên) — hoàn
thiện thêm cho VNPay ở trên (GIỮ NGUYÊN các quyết định đó), bịt các case
lỗi/đồng thời còn hở:

- **Mỗi LẦN THỬ có `vnp_TxnRef` RIÊNG** (`payments.attempt_count` +
  `payments.txn_ref`, migration `b2c9d4e7f1a3`) — trước đây `vnp_TxnRef =
  payment.id` cố định, retry (reset "failed"->"pending") dùng lại CÙNG ref nên
  callback của lần thử CŨ đến trễ có thể tác động sang lần thử MỚI (cùng ref,
  cùng số tiền, chữ ký vẫn hợp lệ). Giờ mỗi `build_payment_url()` tăng
  `attempt_count`, đặt `txn_ref = "{id}A{attempt}"`; `process_callback()` tra
  Payment theo `txn_ref` HIỆN TẠI — callback mang ref lần thử đã bị thay thế
  KHÔNG khớp dòng nào -> từ chối stale, chỉ lần thử MỚI NHẤT được tin (đúng
  hơn với spec VNPay: `vnp_TxnRef` nên duy nhất theo từng giao dịch).
- **Tạo giao dịch khóa Order** (`SELECT ... FOR UPDATE`, cùng kỷ luật
  `checkout()`) — 2 request create/retry đồng thời cho cùng đơn serialize:
  request đầu tạo Payment rồi commit, request sau tái sử dụng (tăng attempt),
  KHÔNG đụng UNIQUE(order_id) gây 500. `process_callback()` khóa theo thứ tự
  Order -> Payment (CÙNG thứ tự `build_payment_url`) tránh deadlock giữa 1
  callback và 1 retry đồng thời.
- **Callback THÀNH CÔNG đến SAU khi đơn đã hủy** — ghi nhận TRUNG THỰC
  (`status=success` + `transaction_id`, KHÔNG mất dấu tiền VNPay đã thu),
  KHÔNG hoàn kho lần 2 (kho đã hoàn lúc hủy), KHÔNG "hồi sinh" đơn. Log cảnh
  báo "CẦN HOÀN TIỀN thủ công". "order cancelled + payment success" = cờ đối
  soát hoàn tiền thủ công.
- **Hủy đơn ĐÃ thanh toán online**: Customer tự hủy -> CHẶN 409
  (`order_service.OrderAlreadyPaidError`, "liên hệ hỗ trợ để hoàn tiền");
  Admin vẫn hủy được qua `PUT /orders/{id}/status` (có thẩm quyền, hoàn tiền
  thủ công) + log cảnh báo. `OrderDetailView.tsx` ẩn nút "Hủy đơn" khi đã
  thanh toán thành công (không hiện nút chỉ để nhận 409, cùng nguyên tắc
  "không nút giả").
- **Đường phục hồi khi khởi tạo VNPay thất bại** (#1): `OrderDetailView.tsx`
  hiện nút "Thanh toán qua VNPay" cho MỌI đơn `pending` chưa thanh toán thành
  công — KỂ CẢ chưa có dòng Payment (VD `POST /payments/create` từng 503 lúc
  checkout trước khi kịp tạo Payment; cũng cho đơn COD chuyển sang trả
  online). Nhãn thành "Thanh toán lại" nếu đã có giao dịch pending/failed.
- **Auto-refund (hoàn tiền tự động) NGOÀI PHẠM VI** — cần VNPay refund API +
  UI Admin, xem `docs/KNOWN_TODOS.md` #31; hiện chỉ log + hiện trạng thái ở
  chi tiết đơn để đối soát thủ công.

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
thành công: gọi `refreshCart()` (GET /cart, task "Sửa đồng bộ giỏ hàng sau
checkout" - thay `clearCart()`/DELETE cũ) để đồng bộ badge Header (Context
không tự biết `POST /orders` đã xóa `cart_items` trong transaction) rồi
`router.push("/checkout/success?order_id=<id>")`. KHÔNG gửi DELETE /cart:
Backend đã xóa rồi nên DELETE là THỪA + có race (khách thêm món ở tab khác
trong khoảng đó, DELETE đến muộn xóa nhầm món mới); GET chỉ đọc, trả đúng
trạng thái hiện tại. `clearCart` đã BỎ khỏi `CartContext` (chỉ dùng đúng chỗ
này), thay bằng `refreshCart` (bọc `fetchCart` sẵn có).

**Route xác nhận là `/checkout/success?order_id=<id>`, KHÔNG PHẢI
`/orders/[id]/confirmation`** (có chủ đích) — đây là bước cuối nhất thời của
checkout, không phải thuộc tính bền vững của đơn hàng; đặt dưới
`/orders/[id]/...` sẽ khiến trang trông như "vừa đặt xong" mỗi lần bookmark
dù đơn có thể đã giao lâu. `/orders/[id]` đã hoàn thiện thật (task "Hoàn
thiện toàn bộ luồng đơn hàng Customer") - xem đoạn riêng bên dưới, KHÔNG còn
là stub tĩnh của task 4.3.3.
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

`OrdersView.tsx` - 2 hoàn thiện thêm (task "Hoàn thiện toàn bộ luồng đơn hàng
Customer"): (1) `loadError` state riêng (khác `orders.length === 0`) khi
`GET /orders` thất bại - hiện nút "Thử lại" gọi lại `fetchOrders()`, KHÔNG
còn im lặng hiện nhầm "Bạn chưa có đơn hàng nào." cho lỗi mạng/5xx thật. (2)
Sau mỗi fetch, nếu trang hiện tại (`?page=`) đã VƯỢT quá `total_pages` thật
trả về VÀ danh sách rỗng (VD vừa hủy đơn CUỐI CÙNG còn hiển thị ở trang 2) -
tự `router.replace()` lùi về trang cuối cùng còn dữ liệu (`Math.max(1,
total_pages)`), không để lại URL trang rỗng trong lịch sử back/forward.

**`app/(customer)/orders/[id]/page.tsx` + `OrderDetailView.tsx`** (hoàn thiện
thật, thay stub cũ task 4.3.3) — `page.tsx` (Server Component) CHỈ parse +
validate `id` (không phải số nguyên dương → "không tìm thấy" ngay, không gọi
API biết trước 422), giao cho `OrderDetailView` (Client Component) xử lý
fetch/state/SSE/hủy đơn, cùng cách tách `OrdersPage`/`OrdersView`.

Phân biệt RÕ 4 loại lỗi `GET /orders/{id}` bằng 1 state machine
(`LoadState`), KHÔNG dùng 1 thông báo lỗi chung chung: **401** (chưa đăng
nhập/token hết hạn) → `router.replace("/login")` NGAY (trang này không có
guard riêng kiểu `AdminAuthGuard`, tự xử lý dựa trên response thật của chính
request `GET /orders/{id}`); **403** (đã đăng nhập nhưng KHÔNG phải chủ đơn)
→ hiện thông báo + link quay lại danh sách, KHÔNG redirect (khác 401, không
phải lỗi phiên đăng nhập); **404** (id không tồn tại) → thông báo tương tự;
**mạng/5xx khác** → thông báo + nút "Thử lại" (gọi lại `fetchOrder()` -
KHÔNG có ý nghĩa cho 403/404 vì lỗi đó không tự hết khi gọi lại nên 2 case
đó cố tình không có nút này).

Đồng bộ SSE (`useOrderStatusStream`, task 5.2.2) trực tiếp vào đơn đang xem —
lọc ĐÚNG `event.order_id === orderId` (kênh Redis theo `user_id`, 1 user có
thể có đơn KHÁC đổi trạng thái trong lúc đang xem đơn này) rồi
**refetch lại toàn bộ** qua `GET /orders/{id}` (KHÔNG tự patch `status` cục
bộ) — cùng nguyên tắc `OrdersView.tsx`/`OrderCard.tsx`, đảm bảo lấy đúng
`updated_at` mới nhất từ Backend thay vì tự suy đoán 1 phần dữ liệu. Nút "Hủy
đơn hàng" (chỉ hiện khi `status === "pending"`, cùng `window.confirm()` +
`PUT /orders/{id}/cancel` như `OrderCard.tsx`) set thẳng state từ response
`OrderRead` trả về, không cần refetch riêng.

**Streaming AI `/ws/chat`** (task 6.1.1–6.1.2) — đã thay placeholder bằng
LLM thật qua `ChatOpenAI`, đổi provider chỉ bằng nhóm biến `LLM_*` (dev dùng
Ollama OpenAI-compatible, production có thể dùng OpenAI). Wire protocol server
→ client là `connected` → nhiều event `chunk` → `done`; nếu LLM lỗi/không có
token đầu trong 12 giây thì gửi `error` và GIỮ kết nối để user thử lại. Frontend
ghép các chunk vào cùng một message assistant và khóa input bằng `isStreaming`
cho tới `done`/`error`/disconnect. Không đặt timeout cho toàn bộ stream; độ dài
đã chặn bởi `LLM_MAX_TOKENS`.

Ngữ cảnh mỗi lượt gồm `SYSTEM_PROMPT` + tối đa 20 message `user`/`assistant`
mới nhất của đúng `session_id`, đọc từ MongoDB theo thứ tự mới→cũ rồi đảo lại
cũ→mới. Router PHẢI lưu message user thành công TRƯỚC khi gọi
`stream_agent_reply()`; service đọc lại message hiện tại từ history và KHÔNG
nhận/nối thêm `user_message` riêng — nếu nối lại sẽ gửi cùng câu hỏi hai lần
cho LLM (regression test ở `tests/test_chat_service.py`). Chỉ lưu message
assistant sau khi stream hoàn tất; lỗi lưu assistant sau khi client đã nhận đủ
chỉ ghi log, không báo thất bại giả cho user.

AI hiện mới hội thoại thuần: CHƯA có RAG/tool truy vấn catalog thật, nên
`SYSTEM_PROMPT` buộc không bịa giá/tồn kho và hướng khách xem catalog. REST
`POST /ai/chat`, history/log APIs vẫn `501`; rate limit Redis vẫn là task kế
tiếp.

**`GET /notifications/orders/stream`** (SSE, task 5.2.1) — xác thực qua JWT ở
query param (`?token=...`), cùng lý do/cách WebSocket (`EventSource` cũng
không cho set custom header) nhưng ĐƠN GIẢN HƠN: lỗi auth raise thẳng
`HTTPException(401/403)` bình thường (xảy ra ở tầng dependency, TRƯỚC khi
`StreamingResponse` được tạo), không cần class exception riêng. `EventSource`
cũng KHÔNG đọc được status code của lần TỰ ĐỘNG reconnect (KNOWN_TODOS #28) —
Frontend (task 5.2.2) cần tự kiểm tra token hết hạn trước khi connect hoặc
chấp nhận thông báo lỗi chung chung, cùng pattern `useChatSocket.ts`.

**Redis Pub/Sub cho SSE** (task 5.2.1) — LẦN ĐẦU TIÊN dự án dùng Redis cho
pub/sub (trước đó CHỈ cache/session/blacklist). Cần thiết vì Backend chạy
Gunicorn NHIỀU worker ở production (`_WORKERS_CAP=4`, task 2.1.2): Admin đổi
trạng thái đơn hàng (`PUT /orders/{id}/status`) có thể được worker A xử lý,
trong khi customer giữ kết nối SSE ở worker B — 2 process riêng biệt, CHỈ
Redis (hạ tầng ngoài process) mới truyền được sự kiện qua worker khác; đây
KHÔNG phải edge case hiếm (round-robin 4 worker khiến phần lớn request rơi
vào worker khác). Channel RIÊNG từng user
(`order_updates:{user_id}`, `app/services/notification_service.py`) — PUBLISH
fire-and-forget (không phải hàng đợi persistent, mất event nếu user không
đang mở SSE đúng lúc là chấp nhận được — `GET /orders/{id}` vẫn là nguồn sự
thật đầy đủ). Middleware log request (`app/core/middleware.py`) loại trừ
path `/api/v1/notifications/` khỏi đo `duration_ms` — số đo theo cách cũ vô
nghĩa cho kết nối mở vô thời hạn (đóng KNOWN_TODOS #3).

**`POST /auth/refresh` + revoke refresh token khi logout** (task "Hoàn thiện
tài khoản và phiên đăng nhập", đóng KNOWN_TODOS #15) — `get_user_from_refresh_token()`
(`app/core/security.py`) verify chữ ký/hạn/`type=refresh` + check blacklist +
`is_active`, tách riêng khỏi `get_current_user` (access token, qua
`Authorization` header) vì refresh token đi qua request body
(`RefreshTokenRequest`), không cần dependency chain FastAPI. **KHÔNG rotate**
refresh token — mỗi lần `/auth/refresh` chỉ cấp access token MỚI, trả nguyên
refresh token client đã gửi (quyết định đã xác nhận: đơn giản hơn, refresh
token vẫn dùng lại được tới khi tự hết hạn `REFRESH_TOKEN_EXPIRE_DAYS` hoặc
bị revoke lúc logout). `blacklist_access_token()` đổi tên thành
`blacklist_token()` (dùng chung cho CẢ access lẫn refresh, logic chỉ phụ
thuộc `jti`/`exp`, không phụ thuộc `type`) — `POST /auth/logout` nhận thêm
body optional `LogoutRequest.refresh_token`, blacklist LUÔN token này nếu
client gửi kèm (đúng `docs/API_SPEC.md` "đưa refresh token vào Redis
blacklist"), best-effort (refresh token thiếu/sai không làm logout thất bại).

**Admin KHÔNG được khóa/mở khóa BẤT KỲ tài khoản Admin nào** (`PUT
/users/{id}/status`, kể cả tự khóa chính mình) — quyết định đã xác nhận,
chặn cả 2 trường hợp (tự khóa + khóa Admin khác) bằng 1 điều kiện duy nhất
(`user.role == UserRole.admin` → 403), tránh 1 Admin duy nhất tự khóa hết hệ
thống hoặc nhiều Admin khóa lẫn nhau. Chỉ áp dụng được cho tài khoản
Customer. `PUT /users/me`/`PUT /users/me/password` implement thật cùng task
này (`user_service.py:update_profile()`/`change_password()`) — `update_profile()`
chỉ ghi đè field client THỰC SỰ gửi (`model_dump(exclude_unset=True)`),
`change_password()` bắt buộc verify đúng `old_password` trước khi đổi (raise
`UserServiceError` → router dịch 400, cùng convention `CartError`).

**`AuthProvider`/`AuthContext`** (`frontend/context/AuthContext.tsx`, đóng
KNOWN_TODOS #22 - `useAuth()` gọi lặp `GET /auth/me`) — đặt ở ROOT layout
(`app/layout.tsx`), KHÔNG đặt trong `(customer)/layout.tsx` như `CartProvider`
vì `AdminAuthGuard` (route `admin/`) CŨNG cần đọc chung state này.
`hooks/useAuth.ts` giờ CHỈ còn là lớp mỏng bọc `useContext()` — giữ nguyên
tên + shape trả về (`{user, isAuthenticated, isLoading, logout}`) nên
Header/CartContext/ChatWidget/AdminAuthGuard KHÔNG cần sửa gì. `LoginForm.tsx`
gọi `refetch()` (AuthContext, trả về `User` vừa fetch) thay vì tự gọi riêng
`GET /auth/me` — vừa lấy được `role` để quyết định redirect, vừa cập nhật
state dùng chung ngay lập tức.

`AuthProvider` KHÔNG pre-check `isTokenExpired()` trước khi gọi `/auth/me`
(khác bản `useAuth.ts` cũ) — cố tình để access token hết hạn vẫn được gọi
THẬT, response interceptor (`lib/axios.ts`) tự refresh silent + retry đúng 1
lần nếu refresh token còn hợp lệ (giữ đăng nhập xuyên phiên dù access token
hết hạn 60 phút) — nhiều request 401 gần như đồng thời CHỈ gọi
`POST /auth/refresh` ĐÚNG 1 LẦN (`refreshPromise` dùng chung, các request
401 khác đợi cùng promise). Refresh gọi qua `refreshApi` — instance axios
RIÊNG, không gắn interceptor nào, tránh đệ quy vào chính interceptor này nếu
refresh thất bại. Access token mới ghi LẠI ĐÚNG storage cũ
(`isTokenPersisted()`, `lib/auth.ts`) — không tự đổi "Ghi nhớ đăng nhập"
(localStorage) và session-only (sessionStorage) giữa chừng phiên.

Refresh thất bại (không có refresh token/hết hạn/bị revoke) → dọn token +
điều hướng `/login`, NHƯNG chỉ khi request gốc KHÔNG đánh dấu
`skipAuthRedirect: true` — cờ này dùng cho lần gọi `GET /auth/me`/`POST
/auth/logout` NỀN lúc `AuthProvider` mount/logout (chạy trên MỌI trang kể cả
trang công khai), tránh đá user đang xem trang công khai (home, catalog...)
sang `/login` chỉ vì có token cũ/hết hạn nhiều ngày trước còn sót trong
storage — đã tự verify qua browser: session chết (refresh token cũng hỏng)
trên `/orders` (có `RequireAuth`) → điều hướng `/login` qua GUARD; session
chết y hệt trên `/` (trang công khai) → ở lại `/`, chỉ âm thầm coi như chưa
đăng nhập. `RequireAuth.tsx` (`components/layout/RequireAuth.tsx`) là guard
dùng chung cho `/cart`, `/checkout`, `/orders` — chặn TRƯỚC khi nội dung con
kịp fetch/render (trước đây `/cart` tự trả "giỏ hàng trống" và `/orders` hiện
nhầm "chưa có đơn hàng nào" cho user CHƯA đăng nhập, khác hẳn case đã đăng
nhập nhưng chưa có dữ liệu).

`app/profile/page.tsx` (trang hồ sơ) — route TOP-LEVEL, KHÔNG nằm trong
`(customer)/` hay `admin/` (dùng chung CẢ 2 role) - tự guard bằng `useAuth()`
trực tiếp, không phụ thuộc `CartProvider`/`AdminAuthGuard`. Link vào trang
này đặt ở dropdown user (`Header.tsx`, Customer) VÀ `Sidebar.tsx` (Admin).

**Review sản phẩm** (`GET`/`POST /products/{id}/reviews`, `GET`/`DELETE
/reviews`, task "Hoàn thiện review sản phẩm") — implement thật thay 3
endpoint `501` cũ (task 3.2.1-3.2.3 chỉ thiết kế schema + tạo index qua
`backend/scripts/create_mongo_indexes.py`, KHÔNG có logic router). Đây là
lần ĐẦU TIÊN trong dự án 1 request kết hợp CẢ MySQL (verify mua hàng) LẪN
MongoDB (đọc/ghi review) trong cùng 1 luồng.

`POST /products/{id}/reviews` nhận `order_id` do CLIENT CHỈ ĐỊNH (KHÔNG phải
Backend tự chọn - quyết định đã xác nhận: user có thể mua sản phẩm này ở
NHIỀU đơn `delivered` khác nhau, tự chọn gắn review vào đơn nào, Frontend tự
lọc qua `GET /orders?status=delivered` client-side, KHÔNG cần thêm API mới).
`review_service.verify_purchase()` verify LẠI 3 điều kiện, mỗi điều kiện 1
message lỗi RIÊNG (không gộp chung mơ hồ như `_unauthorized()` - đây không
phải bối cảnh bảo mật, user có quyền biết chính xác lý do): `order_id` đúng
là của `current_user`, đơn đã `delivered`, đơn chứa ĐÚNG sản phẩm đang review.

**Unique index `(user_id, order_id, product_id)` + compound `(product_id,
is_deleted, created_at)` ĐÃ CÓ SẴN THẬT** trên MongoDB dev (task 3.2.3 chạy
tay `backend/scripts/create_mongo_indexes.py` từ trước - phát hiện lúc verify
task này, KHÔNG cần tạo lại, main.py KHÔNG tự tạo index lúc khởi động, đúng
quyết định đã ghi trong docstring script đó). `tests/conftest.py` có fixture
`mongo_db` riêng (database `<MONGO_DB_NAME>_test`) gọi LẠI đúng hàm
`create_mongo_indexes()` trong script cho DB test, tránh định nghĩa index
trùng lặp 2 nơi.

`response_model_by_alias=False` bắt buộc ở CẢ 3 route trả `Review*Read`
(`app/routers/review.py`) — `id: PyObjectId = Field(alias="_id")` mặc định bị
FastAPI serialize theo alias (`response_model_by_alias=True` mặc định), lộ
`_id` (quy ước nội bộ MongoDB) ra JSON thay vì `id` như mọi resource khác
trong API - tự bắt lỗi này lúc viết test (`KeyError: 'id'`), không phải suy
đoán trước.

`GET /reviews` (Admin, phân trang + lọc `product_id`/`is_deleted`) và trang
`/admin/reviews` (`ReviewTable.tsx`) là MỞ RỘNG thêm (quyết định đã xác
nhận) - KHÔNG có trong `docs/API_SPEC.md` bản gốc task 3.2.2/6.x (bản gốc
chỉ có `DELETE /reviews/{id}`). KHÁC `list_product_reviews()` (luôn ẩn
`is_deleted=true`): Admin thấy CẢ review đã xóa mềm (đúng mục đích "audit
trail" của thiết kế soft-delete) - `is_deleted` chỉ lọc khi Admin chọn rõ.
`ReviewAdminRead` có thêm `product_name` (JOIN sang MySQL theo BATCH, không
N+1) vì document Mongo chỉ denormalize `user_name`, không có tên sản phẩm.

XÓA review (Admin) và GỬI review (Customer) đều KHÔNG gọi lại API list toàn
bộ sau khi xong - `ReviewTable.tsx`/`page.tsx` patch 1 dòng cục bộ
(`is_deleted: true`, biết chắc kết quả vì soft-delete luôn xác định);
`ProductReviews.tsx` gọi lại CHÍNH XÁC `fetchReviews()` (chỉ trang review,
KHÔNG phải cả trang sản phẩm) sau khi gửi thành công, và loại `order_id` vừa
dùng khỏi danh sách đơn hợp lệ (tránh bấm gửi lại ngay, nhận 409 oan) - danh
sách đơn hợp lệ KHÔNG tự biết review nào đã tồn tại (Frontend không
pre-check trùng), lỗi 409 thật từ Backend vẫn là tuyến phòng thủ cuối cùng
nếu user reload trang rồi thử lại đúng đơn đã dùng.

`StarRating.tsx` (`components/product/`) - component rating ĐẦU TIÊN trong
dự án, dùng chung CẢ chế độ xem (điểm trung bình, từng review) LẪN chế độ
nhập (form viết review) qua prop `onChange` có/không.

**Luồng dữ liệu chính**:
- **MySQL** (qua SQLAlchemy): dữ liệu quan hệ — User, Product, Category, Cart, Order.
- **MongoDB** (qua PyMongo): dữ liệu phi cấu trúc — Chat log (AI Agent), Review.
- **Redis**: cache, session/token blacklist khi logout, Pub/Sub cho SSE cập
  nhật trạng thái đơn hàng (task 5.2.1), **rate limit cho AI chat**
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
- **`/ws/chat` xác thực qua JWT ở QUERY PARAM, không phải Authorization
  header** (task 5.1.1, `authenticate_websocket` trong `ai_chat.py`) —
  trình duyệt không cho set custom header lúc mở WebSocket handshake, đây
  là pattern chuẩn cho WS auth. Dùng LẠI `get_token_payload`/
  `get_current_user` (gọi trực tiếp như hàm thường, không qua `Depends()`
  kiểu HTTP) — raise `WebSocketException` (4001 token thiếu/sai/hết hạn/
  blacklist, 4003 đúng token nhưng không phải Customer) TRƯỚC `accept()`.
  Cả Mongo (pymongo) LẪN Redis (redis-py, qua check blacklist) đều PHẢI bọc
  `asyncio.to_thread()` khi gọi từ handler async này, đúng note đã có ở
  `database.py`. **Giới hạn cần biết**: WebSocket API trình duyệt thật
  KHÔNG đọc được close code 4001/4003 cho kết nối bị từ chối trước
  `accept()` (luôn báo `1006` chung chung — giới hạn chuẩn WebSocket, không
  phải bug) — chỉ tool test tầng ASGI (`TestClient`) hoặc client ngoài
  trình duyệt mới thấy đúng code; frontend cần tự kiểm tra token hết hạn
  trước khi connect hoặc chấp nhận thông báo lỗi chung chung, xem
  `docs/KNOWN_TODOS.md` #2.
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
