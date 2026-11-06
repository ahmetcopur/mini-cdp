import os

# The app reads these when it is imported, so they are set first. Docker Compose and
# CI set their own values, which are kept.
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-bytes-long")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.auth import API_KEY, create_token  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

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
def make_client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield lambda headers=None: TestClient(app, headers=headers)
    app.dependency_overrides.clear()


def bearer(role):
    return {"Authorization": f"Bearer {create_token(1, role)}"}


@pytest.fixture
def client(make_client):
    """Logged in as an admin and sending the store's API key, so it can call everything."""
    return make_client({**bearer("admin"), "X-API-Key": API_KEY})


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
