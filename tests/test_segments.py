from datetime import datetime, timedelta, timezone


def segment_user_ids(client, rules, name="test"):
    segment = client.post("/segments", json={"name": name, "rules": rules}).json()
    response = client.get(f"/segments/{segment['id']}/users").json()
    assert response["count"] == len(response["users"])
    return [u["id"] for u in response["users"]]


def test_big_spenders(client, make_user, make_product, track):
    rich = make_user()
    poor = make_user()
    expensive = make_product(price_cents=50000)
    cheap = make_product(price_cents=500)
    track(rich, expensive)
    track(poor, cheap)

    rules = [{"field": "total_spent_cents", "op": "gte", "value": 10000}]
    assert segment_user_ids(client, rules) == [rich]


def test_country_and_purchase_count(client, make_user, make_product, track):
    turkish_buyer = make_user("TR")
    german_buyer = make_user("DE")
    turkish_browser = make_user("TR")
    product = make_product()
    track(turkish_buyer, product)
    track(turkish_buyer, product)
    track(german_buyer, product)
    track(german_buyer, product)
    track(turkish_browser, product, "view")

    rules = [
        {"field": "country", "op": "eq", "value": "TR"},
        {"field": "purchase_count", "op": "gte", "value": 2},
    ]
    assert segment_user_ids(client, rules) == [turkish_buyer]


def test_users_without_events_match_zero_counts(client, make_user):
    user = make_user()
    rules = [{"field": "purchase_count", "op": "eq", "value": 0}]
    assert segment_user_ids(client, rules) == [user]


def test_inactive_users(client, make_user, make_product, track):
    active = make_user()
    inactive = make_user()
    product = make_product()
    now = datetime.now(timezone.utc)
    track(active, product, "view", now - timedelta(days=2))
    track(inactive, product, "view", now - timedelta(days=45))

    inactive_rules = [{"field": "days_since_last_event", "op": "gt", "value": 30}]
    assert segment_user_ids(client, inactive_rules) == [inactive]

    active_rules = [{"field": "days_since_last_event", "op": "lte", "value": 7}]
    assert segment_user_ids(client, active_rules, name="active") == [active]


def test_invalid_rules(client):
    bad_rules = [
        [{"field": "country", "op": "gt", "value": "TR"}],
        [{"field": "purchase_count", "op": "gt", "value": "many"}],
        [{"field": "days_since_last_event", "op": "eq", "value": 3}],
        [{"field": "favorite_color", "op": "eq", "value": "red"}],
        [],
    ]
    for rules in bad_rules:
        response = client.post("/segments", json={"name": "bad", "rules": rules})
        assert response.status_code == 422, rules


def test_pagination(client, make_user):
    for _ in range(5):
        make_user()
    client.post("/segments", json={"name": "all", "rules": [{"field": "purchase_count", "op": "gte", "value": 0}]})

    response = client.get("/segments/1/users", params={"limit": 2, "offset": 2}).json()
    assert response["count"] == 5
    assert len(response["users"]) == 2


def test_missing_segment(client):
    assert client.get("/segments/1/users").status_code == 404
