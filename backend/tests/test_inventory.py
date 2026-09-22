from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.inventory import InventoryAdjustment
from app.models.product import Product
from app.schemas.inventory import InventoryAdjustCreate
from app.services.inventory_service import adjust_stock
from tests.test_order import (_admin_headers, _customer_headers, _create_category,
                              _create_product, _add_to_cart, VALID_CHECKOUT_PAYLOAD)

URL = "/api/v1/admin/inventory"


@pytest.fixture
def setup_inventory(db):
    product = _create_product(db, _create_category(db).id, stock_quantity=10)
    return product.id, _admin_headers(db)


def send(client, setup, change=5, reason="restock", key=None, **extra):
    pid, headers = setup
    return client.post(URL + "/adjust", headers={**headers, "Idempotency-Key": key or uuid4().hex}, json={
        "product_id": pid, "change_quantity": change, "reason": reason, **extra,
    })


@pytest.mark.parametrize("change,reason,expected", [(5,"restock",15),(-3,"damage",7),(2,"audit",12),(-10,"audit",0)])
def test_valid(client, db, setup_inventory, change, reason, expected):
    r = send(client, setup_inventory, change, reason)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["stock_before"] == 10
    assert r.json()["data"]["stock_after"] == expected
    db.rollback()  # End the observer session REPEATABLE READ snapshot.
    assert db.get(Product, setup_inventory[0]).stock_quantity == expected
    db.rollback()
    assert db.query(InventoryAdjustment).count() == 1


@pytest.mark.parametrize("change,reason", [(0,"restock"),(True,"restock"),("2","restock"),(1.5,"restock"),(-1,"restock"),(1,"damage"),(1,"invalid")])
def test_invalid(client, setup_inventory, change, reason):
    assert send(client, setup_inventory, change, reason).status_code == 422


def test_note_and_key_validation(client, setup_inventory):
    assert send(client, setup_inventory, note="x"*501).status_code == 422
    assert send(client, setup_inventory, key=" ").status_code == 422


def test_auth(client, db, setup_inventory):
    for headers, status in [({},401), (_customer_headers(db),403)]:
        for path in ["/low-stock", "/adjustments"]:
            assert client.get(URL+path, headers=headers).status_code == status
        assert send(client, (setup_inventory[0], headers)).status_code == status


def test_missing_and_insufficient(client, db, setup_inventory):
    assert send(client, (999999, setup_inventory[1])).status_code == 404
    assert send(client, setup_inventory, -11, "damage").status_code == 409
    assert db.query(InventoryAdjustment).count() == 0


def test_replay_after_zero_stock_and_conflict(client, db, setup_inventory):
    first = send(client, setup_inventory, -10, "damage", key="same")
    second = send(client, setup_inventory, -10, "damage", key="same")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert send(client, setup_inventory, 2, "restock", key="same").status_code == 409
    db.rollback()
    assert db.query(InventoryAdjustment).count() == 1


def test_rollback(db, setup_inventory, monkeypatch):
    # Force failure after both writes were flushed, before commit.
    def fail():
        raise RuntimeError("commit unavailable")
    with Session(db.bind) as session:
        monkeypatch.setattr(session, "commit", fail)
        from app.models.user import User, UserRole
        admin_id = db.query(User).filter_by(role=UserRole.admin).one().id
        with pytest.raises(RuntimeError):
            adjust_stock(session, admin_id, "rollback", InventoryAdjustCreate(product_id=setup_inventory[0], change_quantity=5, reason="restock"))
    db.rollback()  # End the observer session REPEATABLE READ snapshot.
    assert db.get(Product, setup_inventory[0]).stock_quantity == 10
    assert db.query(InventoryAdjustment).count() == 0


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_adjustments(client, db, setup_inventory, same_key):
    assert db.bind.dialect.name == "mysql"
    barrier = Barrier(2)
    def worker(i):
        barrier.wait(timeout=10)
        return send(client, setup_inventory, key="same" if same_key else str(i))
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(worker, range(2)))
    assert [r.status_code for r in results] == [200,200], [r.text for r in results]
    db.rollback()  # End the observer session REPEATABLE READ snapshot.
    assert db.get(Product, setup_inventory[0]).stock_quantity == (15 if same_key else 20)
    assert db.query(InventoryAdjustment).count() == (1 if same_key else 2)


def test_concurrent_checkout(client, db, setup_inventory):
    headers = _customer_headers(db)
    _add_to_cart(client, headers, setup_inventory[0], 3)
    barrier = Barrier(2)
    def adjustment():
        barrier.wait(timeout=10)
        return send(client, setup_inventory)
    def checkout():
        barrier.wait(timeout=10)
        return client.post("/api/v1/orders", headers=headers, json=VALID_CHECKOUT_PAYLOAD)
    with ThreadPoolExecutor(2) as pool:
        a, b = pool.submit(adjustment), pool.submit(checkout)
        assert a.result().status_code == 200
        assert b.result().status_code == 201
    db.rollback()  # End the observer session REPEATABLE READ snapshot.
    assert db.get(Product, setup_inventory[0]).stock_quantity == 12


def test_filters(client, db, setup_inventory):
    category = _create_category(db)
    ids = [_create_product(db, category.id, stock_quantity=n).id for n in [0,9,10]]
    headers = setup_inventory[1]
    r = client.get(URL+"/low-stock", headers=headers).json()["data"]
    assert [p["id"] for p in r["items"]] == ids[:2]
    assert client.get(URL+"/low-stock?threshold=0", headers=headers).status_code == 422
    send(client, setup_inventory, key="one")
    send(client, setup_inventory, -1, "damage", key="two")
    params = {"product_id":setup_inventory[0], "reason":"damage", "date_from":str(date.today()), "date_to":str(date.today()), "page_size":1}
    result = client.get(URL+"/adjustments", params=params, headers=headers).json()["data"]
    assert result["total"] == 1
    assert result["items"][0]["reason"] == "damage"
    assert result["items"][0]["admin_id"] > 0
    assert client.get(URL+"/adjustments?page=2&page_size=1", headers=headers).json()["data"]["items"][0]["reason"] == "restock"


def test_cancellation_and_adjustment_concurrent(client, db, setup_inventory):
    headers = _customer_headers(db)
    _add_to_cart(client, headers, setup_inventory[0], 3)
    oid = client.post("/api/v1/orders", headers=headers, json=VALID_CHECKOUT_PAYLOAD).json()["data"]["id"]
    barrier = Barrier(3)
    def worker(i):
        barrier.wait(timeout=10)
        if i == 2:
            return send(client, setup_inventory)
        return client.put(f"/api/v1/orders/{oid}/cancel", headers=headers)
    with ThreadPoolExecutor(3) as pool:
        responses = list(pool.map(worker, range(3)))
    assert sorted(r.status_code for r in responses[:2]) == [200,400]
    assert responses[2].status_code == 200
    db.rollback()
    assert db.get(Product, setup_inventory[0]).stock_quantity == 15


def test_concurrent_same_key_different_payload(client, db, setup_inventory):
    barrier = Barrier(2)
    def worker(change):
        barrier.wait(timeout=10)
        return send(client, setup_inventory, change, key="conflicting")
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(worker, [1,2]))
    assert sorted(r.status_code for r in responses) == [200,409]
    db.rollback()
    record = db.query(InventoryAdjustment).one()
    assert db.get(Product, setup_inventory[0]).stock_quantity == 10 + record.change_quantity
