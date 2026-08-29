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

### Cài đặt lần đầu (first setup)

```bash
git clone <repo-url>
cd AI-Powered-E-Commerce-Platform

cp .env.example .env                  # MYSQL_ROOT_PASSWORD/MYSQL_DATABASE +
                                        # MONGO_INITDB_ROOT_USERNAME/PASSWORD + REDIS_PASSWORD
cp backend/.env.example backend/.env  # JWT_SECRET_KEY + các biến khác Backend cần lúc chạy
                                        # standalone - 3 biến DATABASE_URL/MONGO_URI/REDIS_URL
                                        # trong file này bị docker-compose.yml OVERRIDE tự động
                                        # khi chạy qua compose, KHÔNG cần tự sửa cho khớp.

docker compose up --build
```

Thứ tự khởi động tự động qua `depends_on: condition: service_healthy`:

```
MySQL / MongoDB / Redis lên trước (đợi healthy)
        |
Backend container start
        |
alembic upgrade head   <-- docker-entrypoint.sh, CHỈ apply migration ĐÃ COMMIT
        |               sẵn trong backend/alembic/versions/, KHÔNG tự sinh
        |               migration mới, KHÔNG autogenerate
Backend start (uvicorn --reload)
        |
Frontend lên cuối (đợi Backend healthy)
```

`product-sync-scheduler` cũng chờ MySQL/MongoDB healthy và khởi động song
song với `backend`, nhưng KHÔNG tự chạy migration (dùng lại
`docker-entrypoint.sh` của Backend, script chỉ áp dụng `alembic upgrade
head` khi lệnh khởi động thật sự là `uvicorn`/`gunicorn` — tránh 2 container
đua nhau update `alembic_version` trên MySQL).

Nếu `alembic upgrade head` thất bại (VD mất kết nối MySQL, migration lỗi),
container `backend` DỪNG HẲN — không khởi động `uvicorn`/`gunicorn` với
schema có thể dở dang.

Truy cập: `frontend` — http://localhost:3000, `backend`/Swagger —
http://localhost:8000/docs, `mysql`/`mongodb`/`redis` vẫn publish port ra
host (3306/27017/6379) để debug bằng Workbench/Compass/RedisInsight.

### Seed dữ liệu development

Seed vài category/product mẫu + 1 tài khoản admin — TÁCH BIỆT hoàn toàn
khỏi Alembic migration, KHÔNG tự chạy khi `docker compose up`, chỉ chạy khi
chủ động gọi:

```bash
docker compose exec backend python -m scripts.seed_dev_data
```

An toàn khi chạy lại nhiều lần (idempotent theo `slug`/`email` — dữ liệu đã
tồn tại thì bỏ qua, không tạo trùng). Password admin được hash bằng đúng cơ
chế `hash_password` thật của project (bcrypt qua passlib, tái dùng
`scripts/seed_admin.py`), không lưu plain text.

### MongoDB indexes

Tạo/cập nhật index cho 3 collection (`chat_logs`, `reviews`,
`product_catalog_sync`) — chạy THỦ CÔNG, không tự động khi backend khởi
động (có chủ đích, xem giải thích trong chính file script):

```bash
docker compose exec backend python -m scripts.create_mongo_indexes
```

`create_index()` của PyMongo idempotent (chạy lại nhiều lần không tạo
trùng), chỉ cần chạy lại khi thêm/đổi index mới trong script.

### Reset môi trường development

```bash
docker compose down -v
docker compose up --build
```

`-v` xóa LUÔN named volume MySQL/MongoDB (mất toàn bộ data) — Redis vốn đã
luôn mất khi `down` (tmpfs, có chủ đích). CHỈ dùng khi thật sự muốn bắt đầu
lại từ đầu (VD test lại toàn bộ migration từ DB rỗng), KHÔNG dùng trong
workflow phát triển hàng ngày.

### Tạo migration mới

Quy trình giữ nguyên, KHÔNG đổi bởi việc entrypoint tự `alembic upgrade
head` lúc Docker start (bước đó CHỈ áp dụng migration đã tồn tại, KHÔNG bao
giờ tự sinh migration mới):

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```

Developer review file migration sinh ra trong `backend/alembic/versions/` →
commit/PR → sau khi approve/merge, container `backend` khởi động lần kế
tiếp sẽ tự `alembic upgrade head` migration này (hoặc chạy tay, xem mục
dưới).

### Chạy migration thủ công

```bash
docker compose exec backend alembic upgrade head
```

Dùng khi cần apply migration ngay mà không muốn restart container `backend`.

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
