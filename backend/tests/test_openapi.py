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


def test_protected_endpoint_reaches_placeholder_with_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 501


def test_public_endpoint_does_not_require_auth(client: TestClient) -> None:
    response = client.get("/api/v1/products")
    assert response.status_code == 501
