import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# set a temp DB before importing app
fd, path = tempfile.mkstemp()
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{path}"

from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_db():
    init_db()
    yield
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_and_list_products():
    r = client.post("/products", json={"name": "Apple", "price": 1.5})
    assert r.status_code == 201
    prod = r.json()
    assert prod["name"] == "Apple"

    r = client.get("/products")
    assert r.status_code == 200
    assert any(p["name"] == "Apple" for p in r.json())

def test_create_sale_and_report():
    # find Apple product id
    prods = client.get("/products").json()
    apple = next(p for p in prods if p["name"] == "Apple")

    r = client.post("/sales", json={"product_id": apple["id"], "quantity": 4})
    assert r.status_code == 201
    sale = r.json()
    assert sale["total"] == pytest.approx(6.0)

    r = client.get("/sales")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = client.get("/reports/daily")
    assert r.status_code == 200
    rep = r.json()
    assert rep["total_revenue"] >= 6.0
    assert rep["total_items"] >= 4