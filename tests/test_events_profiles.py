from datetime import datetime, timedelta, timezone


def test_purchase_stores_price(make_user, make_product, track):
    user = make_user()
    product = make_product(price_cents=2500)

    assert track(user, product, "purchase")["value_cents"] == 2500
    assert track(user, product, "view")["value_cents"] == 0


def test_unknown_product(client, make_user):
    user = make_user()
    response = client.post("/events", json={"user_id": user, "product_id": 42, "type": "view"})
    assert response.status_code == 404


def test_unknown_event_type(client, make_user, make_product):
    body = {"user_id": make_user(), "product_id": make_product(), "type": "click"}
    assert client.post("/events", json=body).status_code == 422


def test_batch_insert(client, make_user, make_product):
    user = make_user()
    product = make_product()
    body = [{"user_id": user, "product_id": product, "type": "view"} for _ in range(10)]

    response = client.post("/events/batch", json=body)
    assert response.json() == {"inserted": 10}
    assert len(client.get(f"/users/{user}/events").json()) == 10


def test_batch_with_unknown_user_inserts_nothing(client, make_user, make_product):
    user = make_user()
    product = make_product()
    body = [
        {"user_id": user, "product_id": product, "type": "view"},
        {"user_id": 999, "product_id": product, "type": "view"},
    ]

    assert client.post("/events/batch", json=body).status_code == 404
    assert client.get(f"/users/{user}/events").json() == []


def test_events_newest_first(client, make_user, make_product, track):
    user = make_user()
    product = make_product()
    now = datetime.now(timezone.utc)
    track(user, product, "view", now - timedelta(days=2))
    track(user, product, "purchase", now - timedelta(days=1))

    events = client.get(f"/users/{user}/events").json()
    assert [e["type"] for e in events] == ["purchase", "view"]


def test_profile(client, make_user, make_product, track):
    user = make_user()
    shoe = make_product(category="shoes", price_cents=3000)
    bag = make_product(category="bags", price_cents=5000)
    track(user, shoe, "view")
    track(user, shoe, "view")
    track(user, shoe, "purchase")
    track(user, bag, "add_to_cart")
    track(user, bag, "purchase")

    profile = client.get(f"/users/{user}/profile").json()
    assert profile["view_count"] == 2
    assert profile["add_to_cart_count"] == 1
    assert profile["purchase_count"] == 2
    assert profile["total_spent_cents"] == 8000
    assert profile["favorite_category"] == "shoes"
    assert profile["last_event_at"] is not None


def test_empty_profile(client, make_user):
    profile = client.get(f"/users/{make_user()}/profile").json()
    assert profile["purchase_count"] == 0
    assert profile["total_spent_cents"] == 0
    assert profile["favorite_category"] is None
    assert profile["last_event_at"] is None
