"""Fixtures dùng chung cho pytest.

`client`/`db` chạy trên 1 database MySQL RIÊNG (suy ra từ DATABASE_URL trong
.env, thêm hậu tố "_test") - dùng MySQL thật thay vì SQLite vì model User có
DDL đặc thù MySQL (ENUM gốc, "ON UPDATE CURRENT_TIMESTAMP" ở updated_at - xem
app/models/user.py) mà SQLite không hiểu cú pháp này. Vì vậy chạy `pytest` cần
có MySQL đang chạy (VD: container `mysql-dev`) và trỏ đúng DATABASE_URL trong
.env - không còn "zero-dependency" như trước.

Database test (VD: `ecommerce_test`) cần được tạo sẵn 1 lần bằng tay:
    docker exec mysql-dev mysql -uroot -p<password> -e "CREATE DATABASE IF NOT EXISTS ecommerce_test;"
Cố tình KHÔNG tự tạo DB ngay trong fixture: mở 2 kết nối liên tiếp (1 kết nối
không chọn DB để CREATE DATABASE, tiếp theo là kết nối có DB) gây lỗi
"Access denied ... 172.17.0.1" không ổn định - lỗi hạ tầng mạng của Docker
Desktop (Windows) khi thương lượng auth plugin caching_sha2_password qua NAT,
không phải lỗi code. Chỉ mở 1 kết nối/test tránh được lỗi này.

Mỗi test được cấp 1 schema sạch (drop_all rồi create_all trước khi yield).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - đăng ký model vào Base.metadata trước khi create_all
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app


def _build_test_database_url() -> str:
    """Lấy DATABASE_URL từ .env, đổi tên DB sang "<db>_test" (dùng chung host/
    user/password với DB dev - không hardcode secret trong test code).

    Dùng render_as_string(hide_password=False) - str(url) mặc định CHE mật khẩu
    thành "***" (tính năng bảo mật của SQLAlchemy để tránh lộ secret khi log),
    nếu dùng str(url) trực tiếp thì connection string sẽ chứa password="***" và
    luôn bị MySQL từ chối (Access denied) dù giá trị thật trong .env đúng.
    """
    url = make_url(get_settings().DATABASE_URL)
    test_url = url.set(database=f"{url.database}_test")
    return test_url.render_as_string(hide_password=False)


@pytest.fixture
def _test_engine() -> Engine:
    """1 schema MySQL sạch dùng chung cho cả `client` và `db` trong 1 test."""
    engine = create_engine(_build_test_database_url())
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(_test_engine: Engine) -> TestClient:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # raise_server_exceptions=False: mặc định TestClient tự raise lại exception
        # ra ngoài test kể cả khi app đã có catch-all Exception handler xử lý đúng
        # và trả về 500 hợp lệ cho client thật (Starlette làm vậy để lộ traceback
        # lúc debug) - tắt đi để test được response 500 thật giống client thật nhận,
        # thay vì phải try/except RuntimeError trong từng test.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def db(_test_engine: Engine) -> Session:
    """Session riêng để test tự seed dữ liệu trực tiếp (VD: tạo user role=admin -
    endpoint /auth/register không cho tự đăng ký admin nên phải insert thẳng qua
    fixture này thay vì gọi API)."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
