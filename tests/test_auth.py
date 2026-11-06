from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth import API_KEY, JWT_SECRET, create_token
from app.models import Account
from app.passwords import hash_password

READS = [
    "/segments",
    "/segments/1/users",
    "/users/1",
    "/users/search?q=a",
    "/users/1/events",
    "/users/1/profile",
    "/users/1/recommendations",
    "/products",
    "/analytics/daily",
    "/analytics/funnel",
    "/analytics/top-products",
]

RULES = [{"field": "purchase_count", "op": "gte", "value": 0}]

ADMIN_WRITES = [
    ("post", "/segments", {"name": "test", "rules": RULES}),
    ("put", "/segments/1", {"name": "test", "rules": RULES}),
    ("delete", "/segments/1", None),
]

STORE_WRITES = [
    ("/users", {"external_id": "cust-1"}),
    ("/products", {"sku": "sku-1", "name": "Shoe", "category": "shoes", "price_cents": 100}),
    ("/events", {"user_id": 1, "product_id": 1, "type": "view"}),
    ("/events/batch", [{"user_id": 1, "product_id": 1, "type": "view"}]),
]


def bearer(role):
    return {"Authorization": f"Bearer {create_token(1, role)}"}


def token_header(payload, secret=JWT_SECRET):
    return {"Authorization": f"Bearer {jwt.encode(payload, secret, algorithm='HS256')}"}


@pytest.fixture
def account(db):
    db.add(Account(email="viewer@example.com", password_hash=hash_password("right-password"), role="viewer"))
    db.commit()


def test_login_returns_working_token(make_client, account):
    response = make_client().post("/auth/login", json={"email": "viewer@example.com", "password": "right-password"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "viewer"

    viewer = make_client({"Authorization": f"Bearer {body['access_token']}"})
    assert viewer.get("/segments").status_code == 200


def test_login_rejects_wrong_password_and_unknown_email(make_client, account):
    for email, password in [("viewer@example.com", "wrong-password"), ("nobody@example.com", "right-password")]:
        response = make_client().post("/auth/login", json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json()["detail"] == "Wrong email or password"


@pytest.mark.parametrize("path", READS)
def test_reads_need_a_token(make_client, path):
    assert make_client().get(path).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer not-a-token"},
        token_header({"sub": "1", "role": "admin"}, secret="some-other-secret-at-least-32-bytes"),
        token_header({"sub": "1", "role": "admin", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}),
    ],
    ids=["garbage", "wrong-secret", "expired"],
)
def test_bad_tokens_are_rejected(make_client, headers):
    response = make_client(headers).get("/segments")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_viewer_can_read_and_preview(make_client):
    viewer = make_client(bearer("viewer"))
    assert viewer.get("/segments").status_code == 200
    assert viewer.post("/segments/preview", json={"rules": RULES}).json() == {"count": 0}


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_WRITES)
def test_viewer_cannot_change_segments(make_client, method, path, body):
    response = make_client(bearer("viewer")).request(method, path, json=body)
    assert response.status_code == 403


@pytest.mark.parametrize(("path", "body"), STORE_WRITES)
@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-Key": "wrong-key"}, bearer("admin")],
    ids=["no-key", "wrong-key", "admin-token-instead-of-key"],
)
def test_store_endpoints_need_the_api_key(make_client, path, body, headers):
    response = make_client(headers).post(path, json=body)
    assert response.status_code == 401


def test_store_endpoints_work_with_only_the_api_key(make_client):
    store = make_client({"X-API-Key": API_KEY})
    assert store.post("/users", json={"external_id": "cust-1"}).status_code == 201


def test_health_and_docs_are_open(make_client):
    anonymous = make_client()
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get("/docs").status_code == 200
