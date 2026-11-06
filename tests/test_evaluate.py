from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import Event
from scripts.evaluate import evaluate


def test_recommender_beats_popular(db, make_user, make_product, track):
    phone, case, socks = make_product(), make_product(), make_product()
    now = datetime.now(timezone.utc)
    for _ in range(3):
        user = make_user()
        track(user, phone, "purchase", now - timedelta(days=2))
        track(user, case, "purchase", now - timedelta(days=1))
    for _ in range(3):
        track(make_user(), socks)

    # Each phone buyer's hidden case was also bought by the other two phone buyers,
    # but socks are the most popular product.
    assert evaluate(db, k=1) == {"users": 3, "skipped": 0, "recommender": 1.0, "popular": 0.0}


def test_only_users_with_two_purchases_count(db, make_user, make_product, track):
    phone, case = make_product(), make_product()
    buyer, one_purchase = make_user(), make_user()
    track(buyer, phone)
    track(buyer, case)
    track(one_purchase, phone)
    track(one_purchase, case, "view")
    track(one_purchase, case, "add_to_cart")

    assert evaluate(db)["users"] == 1


def test_hides_latest_purchase_and_restores_it(db, make_user, make_product, track):
    phone, case = make_product(), make_product()
    me = make_user()
    now = datetime.now(timezone.utc)
    track(me, phone, "purchase", now - timedelta(days=1))
    track(me, case, "purchase", now - timedelta(days=2))
    for _ in range(2):
        track(make_user(), phone)

    # The phone is the latest purchase even though it was tracked first. Only the
    # hidden phone can be predicted, because nobody else bought the case.
    assert evaluate(db, k=1) == {"users": 1, "skipped": 0, "recommender": 1.0, "popular": 1.0}
    assert db.scalar(select(func.count()).select_from(Event)) == 4


def test_skips_repeat_purchases(db, make_user, make_product, track):
    phone, case = make_product(), make_product()
    now = datetime.now(timezone.utc)
    repeat_buyer, new_buyer = make_user(), make_user()
    track(repeat_buyer, phone, "purchase", now - timedelta(days=3))
    track(repeat_buyer, case, "purchase", now - timedelta(days=2))
    track(repeat_buyer, phone, "purchase", now - timedelta(days=1))
    track(new_buyer, case, "purchase", now - timedelta(days=2))
    track(new_buyer, phone, "purchase", now - timedelta(days=1))

    # The repeat buyer's latest phone is not counted. The new buyer's phone is found
    # because the repeat buyer also bought the case and the phone.
    assert evaluate(db, k=1) == {"users": 1, "skipped": 1, "recommender": 1.0, "popular": 1.0}
