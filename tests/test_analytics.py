from datetime import datetime, timedelta, timezone


def days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


def test_daily_fills_missing_days_with_zeros(client, make_user, make_product, track):
    user = make_user()
    product = make_product(price_cents=2500)
    track(user, product, "view", days_ago(2))
    track(user, product, "purchase", days_ago(2))
    track(user, product, "purchase", days_ago(0))
    track(user, product, "purchase", days_ago(10))

    response = client.get("/analytics/daily", params={"days": 3}).json()

    today = days_ago(0).date()
    assert response == [
        {"date": (today - timedelta(days=2)).isoformat(), "events": 2, "revenue_cents": 2500},
        {"date": (today - timedelta(days=1)).isoformat(), "events": 0, "revenue_cents": 0},
        {"date": today.isoformat(), "events": 1, "revenue_cents": 2500},
    ]


def test_daily_without_events(client):
    response = client.get("/analytics/daily").json()
    assert len(response) == 30
    assert response[-1]["date"] == days_ago(0).date().isoformat()
    assert all(day["events"] == 0 and day["revenue_cents"] == 0 for day in response)


def test_funnel(client, make_user, make_product, track):
    buyer, carter, viewer, repeat_viewer, old_buyer = [make_user() for _ in range(5)]
    product = make_product()
    for user in (buyer, carter, viewer, repeat_viewer):
        track(user, product, "view")
    track(repeat_viewer, product, "view")
    for user in (buyer, carter):
        track(user, product, "add_to_cart")
    track(buyer, product, "purchase")
    track(old_buyer, product, "purchase", days_ago(40))

    assert client.get("/analytics/funnel").json() == {
        "viewed": 4,
        "added_to_cart": 2,
        "purchased": 1,
        "view_to_cart_rate": 0.5,
        "cart_to_purchase_rate": 0.5,
    }


def test_funnel_is_strict(client, make_user, make_product, track):
    complete, skipped_view, skipped_cart = make_user(), make_user(), make_user()
    product = make_product()
    track(complete, product, "purchase", days_ago(2))
    track(complete, product, "add_to_cart", days_ago(1))
    track(complete, product, "view")
    track(skipped_view, product, "add_to_cart")
    track(skipped_view, product, "purchase")
    track(skipped_cart, product, "view")
    track(skipped_cart, product, "purchase")

    # Only the complete user counts past the first step, even though their events
    # happened in reverse order.
    assert client.get("/analytics/funnel").json() == {
        "viewed": 2,
        "added_to_cart": 1,
        "purchased": 1,
        "view_to_cart_rate": 0.5,
        "cart_to_purchase_rate": 1.0,
    }


def test_funnel_without_events(client):
    assert client.get("/analytics/funnel").json() == {
        "viewed": 0,
        "added_to_cart": 0,
        "purchased": 0,
        "view_to_cart_rate": None,
        "cart_to_purchase_rate": None,
    }


def test_top_products(client, make_user, make_product, track):
    users = [make_user() for _ in range(3)]
    cheap, expensive, popular, old, viewed = [make_product(price_cents=price) for price in (100, 900, 100, 100, 100)]
    for user in users:
        track(user, popular)
        track(user, viewed, "view")
        track(user, old, "purchase", days_ago(40))
        track(user, old, "purchase", days_ago(40))
    track(users[0], cheap)
    track(users[0], expensive)

    response = client.get("/analytics/top-products", params={"limit": 2}).json()

    # Ranked by purchases, ties broken by revenue. Old purchases and views don't count.
    assert [(p["product"]["id"], p["purchases"], p["revenue_cents"]) for p in response] == [
        (popular, 3, 300),
        (expensive, 1, 900),
    ]


def test_top_products_without_events(client):
    assert client.get("/analytics/top-products").json() == []


def test_days_must_be_positive(client):
    for path in ("/analytics/daily", "/analytics/funnel", "/analytics/top-products"):
        assert client.get(path, params={"days": 0}).status_code == 422
