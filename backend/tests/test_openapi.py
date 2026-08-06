"""Test cấu hình Swagger/OpenAPI (task 1.2.2)."""

from fastapi.testclient import TestClient


def test_docs_available_in_development(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_has_all_module_tags(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    tag_names = {tag["name"] for tag in schema["tags"]}
    assert tag_names == {
        "Auth",
        "User",
        "Product",
        "Category",
        "Cart",
        "Order",
        "Payment",
        "Review",
        "AI Agent / Chat",
        "Notification",
        "Dashboard Admin",
        "Health Check",
    }


def test_protected_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


# test_protected_endpoint_reaches_placeholder_with_token (task 1.2.2) đã bị xóa:
# get_current_user giờ decode JWT thật (task 1.3.3) nên 1 chuỗi Bearer bất kỳ
# ("fake-token") không còn qua được nữa - hành vi này giờ được test đầy đủ hơn
# ở tests/test_security.py (token thật/hết hạn/sai định dạng/đúng-sai role).


def test_public_endpoint_does_not_require_auth(client: TestClient) -> None:
    """GET /products (task 3.4.1, implement thật) không còn là placeholder
    501 - trả 200 thật (danh sách rỗng, chưa seed sản phẩm nào) là bằng
    chứng RÕ RÀNG hơn hẳn "vượt qua auth rồi rơi vào 501" trước đây."""
    response = client.get("/api/v1/products")
    assert response.status_code == 200
