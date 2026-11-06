import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

connect_args = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(TEST_DATABASE_URL, connect_args=connect_args)
TestSession = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    count = 0

    def make(country="TR"):
        nonlocal count
        count += 1
        response = client.post("/users", json={"external_id": f"user-{count}", "country": country})
        return response.json()["id"]

    return make


@pytest.fixture
def make_product(client):
    count = 0

    def make(category="shoes", price_cents=1000):
        nonlocal count
        count += 1
        body = {"sku": f"sku-{count}", "name": f"Product {count}", "category": category, "price_cents": price_cents}
        return client.post("/products", json=body).json()["id"]

    return make


@pytest.fixture
def track(client):
    def send(user_id, product_id, event_type="purchase", created_at=None):
        body = {"user_id": user_id, "product_id": product_id, "type": event_type}
        if created_at:
            body["created_at"] = created_at.isoformat()
        response = client.post("/events", json=body)
        assert response.status_code == 201
        return response.json()

    return send
