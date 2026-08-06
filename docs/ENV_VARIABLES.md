# Biến môi trường — Tổng hợp (task 2.4.2)

Bảng tra cứu TOÀN BỘ biến môi trường của dự án, gộp từ cả 3 vị trí file
`.env.example` (gốc repo, `backend/`, `frontend/`) — tránh phải lục tìm rải
rác qua từng file khi cần biết 1 biến nào đó dùng ở đâu/để làm gì.

**Khi thêm biến môi trường mới** (VD task 8.1 — VNPay/Momo API key): cập nhật
CẢ 2 nơi — (1) file `.env.example` tương ứng (và `.env.production.example`
nếu biến đó cần giá trị khác ở production), (2) bảng dưới đây. Xem thêm mục
Notes trong `CLAUDE.md`.

**File thật** (`.env`, `backend/.env`, `frontend/.env`, và sau này
`.env.production`...) — KHÔNG BAO GIỜ commit, đã chặn trong `.gitignore` (cả
gốc repo và `frontend/.gitignore` — xem `docs/KNOWN_TODOS.md` nếu có ghi chú
sửa lỗi liên quan). CHỈ file `.env*.example` được phép commit.

---

## Root (`.env.example` / `.env.production.example`) — dùng bởi `docker-compose.yml`

| Biến | Dùng ở đâu | Mô tả |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | Compose service `mysql` (task 2.3.1) | Password root MySQL - PHẢI đổi khi lên production (xem `.env.production.example`). |
| `MYSQL_DATABASE` | Compose service `mysql` | Tên database tạo sẵn lúc MySQL khởi tạo lần đầu - PHẢI khớp với DB name trong `DATABASE_URL` (Backend). |
| `MONGO_INITDB_ROOT_USERNAME` | Compose service `mongodb` (task 2.3.2) | Username root MongoDB (bootstrap qua entrypoint chính thức của image). |
| `MONGO_INITDB_ROOT_PASSWORD` | Compose service `mongodb` | Password root MongoDB - PHẢI đổi khi lên production. |
| `REDIS_PASSWORD` | Compose service `redis` (task 2.3.3, qua `--requirepass` trong `command:`) | Password Redis - PHẢI đổi khi lên production dù data chỉ là cache/session tạm thời (password yếu vẫn là điểm vào tấn công). |

## Backend (`backend/.env.example` / `backend/.env.production.example`)

| Biến | Dùng ở đâu | Mô tả |
|---|---|---|
| `APP_NAME` | `app/core/config.py` → hiển thị trong Swagger title, `/health` | Tên app hiển thị - hiếm khi cần đổi giữa các môi trường. |
| `APP_ENV` | `app/core/config.py` (`settings.is_production`) | `development` hoặc `production` - quyết định tắt Swagger/ReDoc, log level mặc định. **PHẢI đổi thành `production` khi deploy.** |
| `DEBUG` | `app/core/config.py` | Cờ debug chung - **PHẢI đổi thành `False` khi deploy** (tránh lộ traceback chi tiết). |
| `DATABASE_URL` | `app/core/database.py` (SQLAlchemy engine) | Connection string MySQL đầy đủ (`mysql+pymysql://user:pass@host:port/db`). **PHẢI đổi host/password khi deploy** - dev dùng `localhost`/tên service Docker, production trỏ server thật. |
| `MONGO_URI` | `app/core/database.py` (PyMongo `MongoClient`) | Connection string MongoDB - PHẢI có `?authSource=admin` (root user chỉ tồn tại ở DB `admin`, xem `docs/KNOWN_TODOS.md` #7). **PHẢI đổi khi deploy.** |
| `MONGO_DB_NAME` | `app/core/database.py` (`get_mongo_db()`) | Tên database MongoDB app dùng (KHÁC `authSource=admin` trong `MONGO_URI`) - hiếm khi cần đổi giữa các môi trường. |
| `REDIS_URL` | `app/core/database.py` (`redis.from_url`) | Connection string Redis, cú pháp `redis://:<password>@host:port/db` (KHÔNG có username, khác MySQL/Mongo). **PHẢI đổi khi deploy.** |
| `JWT_SECRET_KEY` | `app/core/security.py` (ký/verify JWT) | Secret ký JWT - **PHẢI đổi thành giá trị random mạnh khi deploy** (rủi ro bảo mật cao nhất nếu lộ/dùng giá trị dev). |
| `JWT_ALGORITHM` | `app/core/security.py` | Thuật toán JWT (`HS256`) - hiếm khi cần đổi. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `app/core/security.py` (`create_access_token`) | Thời hạn access token (phút) - có thể giữ nguyên hoặc rút ngắn cho production tùy chính sách bảo mật. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `app/core/security.py` (`create_refresh_token`) | Thời hạn refresh token (ngày) - tương tự trên. |
| `OPENAI_API_KEY` | `app/core/config.py` (khai báo, CHƯA có code nào dùng - task 6.x) | API key OpenAI cho AI Agent - **PHẢI có giá trị thật trước khi task 6.x chạy được**, hiện để trống. |
| `PORT` | `gunicorn_conf.py` (CHỈ `Dockerfile.prod`, KHÔNG dùng ở dev) | Port Gunicorn bind - default `8000`, đổi nếu hosting yêu cầu port khác. |
| `GUNICORN_WORKERS` | `gunicorn_conf.py` (CHỈ production) | Số worker process - default tự tính theo CPU (giới hạn trần 4), **NÊN set thẳng theo CPU thật của server production** thay vì để tự động (xem comment trong `gunicorn_conf.py`). |
| `GUNICORN_TIMEOUT` | `gunicorn_conf.py` (CHỈ production) | Giây chờ trước khi Gunicorn coi worker bị treo và restart - default `30`. |
| `GUNICORN_GRACEFUL_TIMEOUT` | `gunicorn_conf.py` (CHỈ production) | Giây cho phép worker xử lý nốt request dang dở lúc restart/shutdown - default `30`. |
| `GUNICORN_LOG_LEVEL` | `gunicorn_conf.py` (CHỈ production) | Mức log Gunicorn (access/error log) - default `info`. |

## Frontend (`frontend/.env.example` / `frontend/.env.production.example`)

| Biến | Dùng ở đâu | Mô tả |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `lib/axios.ts` (`baseURL`) | URL gốc gọi Backend API - PHẢI là URL trình duyệt gọi được (KHÔNG PHẢI tên service Docker/`host.docker.internal`, xem `CLAUDE.md`). **PHẢI đổi sang domain thật khi deploy** - lưu ý với `Dockerfile.prod` phải truyền qua `--build-arg` lúc `docker build`, đọc file `.env` lúc `docker run` KHÔNG có tác dụng (xem `docs/KNOWN_TODOS.md` #5). |

---

## Chưa có trong `.env` nhưng đang hard-code trong code (phát hiện lúc rà soát task 2.4.2)

- **`allow_origins=["*"]`** (CORS, `backend/app/main.py`) — hard-code, đã có
  sẵn `# TODO: giới hạn allow_origins về domain thật của frontend trước khi
  lên production.` ngay trong code. CHƯA đưa vào `.env` ở task này (phạm vi
  2.4.2 là tổ chức lại file .env hiện có, không đổi code) - cân nhắc thêm biến
  `CORS_ALLOWED_ORIGINS` (danh sách domain, phân tách bởi dấu phẩy) đọc qua
  `app/core/config.py` ở 1 task riêng trước khi thực sự deploy (task 7.x) -
  hiện `allow_origins=["*"]` chấp nhận được cho dev (mọi origin đều gọi được,
  tiện test) nhưng KHÔNG AN TOÀN nếu giữ nguyên ở production (bất kỳ website
  nào cũng gọi được API kèm cookie/credential của user).
