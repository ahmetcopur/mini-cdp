from datetime import datetime, timedelta, timezone


def recommended(client, user_id, limit=5):
    response = client.get(f"/users/{user_id}/recommendations", params={"limit": limit})
    assert response.status_code == 200
    return [(r["product"]["id"], r["reason"]) for r in response.json()]


def test_bought_together_ranking(client, make_user, make_product, track):
    me, a, b, c = make_user(), make_user(), make_user(), make_user()
    phone, case, charger, socks = make_product(), make_product(), make_product(), make_product()

    track(me, phone)
    for other in (a, b, c):
        track(other, phone)
        track(other, case)
    track(a, charger)
    track(b, charger)
    track(c, socks)

    result = recommended(client, me, limit=3)
    assert result == [(case, "bought_together"), (charger, "bought_together"), (socks, "bought_together")]


def test_never_recommends_owned_products(client, make_user, make_product, track):
    me, other = make_user(), make_user()
    phone, case = make_product(), make_product()
    track(me, phone)
    track(me, case)
    track(other, phone)
    track(other, case)

    ids = [product_id for product_id, _ in recommended(client, me)]
    assert phone not in ids
    assert case not in ids


def test_falls_back_to_popular(client, make_user, make_product, track):
    new_user = make_user()
    buyers = [make_user() for _ in range(3)]
    hit, flop, old_hit = make_product(), make_product(), make_product()
    for buyer in buyers:
        track(buyer, hit)
    track(buyers[0], flop)
    old = datetime.now(timezone.utc) - timedelta(days=60)
    for buyer in buyers:
        track(buyer, old_hit, "purchase", old)

    assert recommended(client, new_user) == [(hit, "popular"), (flop, "popular")]


def test_views_do_not_count(client, make_user, make_product, track):
    me, other = make_user(), make_user()
    phone, case = make_product(), make_product()
    track(me, phone)
    track(other, phone)
    track(other, case, "view")

    assert recommended(client, me) == []


def test_unknown_user(client):
    assert client.get("/users/1/recommendations").status_code == 404
