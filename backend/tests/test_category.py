"""Test GET /categories (task 4.2.1) - end-to-end qua HTTP thật, MySQL thật."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category


def _create_category(db: Session, name: str) -> Category:
    category = Category(name=name, slug=f"cat-{name}-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def test_list_categories_empty(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_categories_returns_created_categories_sorted_by_name(client: TestClient, db: Session) -> None:
    _create_category(db, "Vải dệt")
    _create_category(db, "Gốm sứ")

    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()["data"]
    names = [item["name"] for item in data]
    assert names == sorted(names)
    assert "Gốm sứ" in names
    assert "Vải dệt" in names


def test_list_categories_id_is_int_not_string(client: TestClient, db: Session) -> None:
    """Guard cho bug đã có ở ProductRead cũ (docs/KNOWN_TODOS.md #14) -
    CategoryRead.id PHẢI là int (khớp BigInteger thật của model), không phải
    str như schema cũ trước khi sửa ở task 4.2.1."""
    category = _create_category(db, "Trang sức")

    response = client.get("/api/v1/categories")
    data = response.json()["data"]
    match = next(item for item in data if item["id"] == category.id)
    assert isinstance(match["id"], int)
