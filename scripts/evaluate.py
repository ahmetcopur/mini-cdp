from collections import defaultdict

from sqlalchemy import delete, desc, func, select

from app.database import SessionLocal
from app.models import Event
from app.recommendations import recommend

K = 5


def purchases_to_hide(db):
    rows = db.execute(
        select(Event.user_id, Event.id, Event.product_id)
        .where(Event.type == "purchase")
        .order_by(Event.created_at, Event.id)
    )
    purchases = defaultdict(list)
    for user_id, event_id, product_id in rows:
        purchases[user_id].append((event_id, product_id))

    hidden = {}
    skipped = 0
    for user_id, events in purchases.items():
        if len(events) < 2:
            continue
        event_id, product_id = events[-1]
        # Neither method recommends products the user already owns, so a repeat
        # purchase can never be a hit. Only first-time purchases are counted.
        if product_id in [earlier for _, earlier in events[:-1]]:
            skipped += 1
        else:
            hidden[user_id] = (event_id, product_id)
    return hidden, skipped


def most_popular(db, user_id, limit):
    bought = select(Event.product_id).where(Event.user_id == user_id, Event.type == "purchase")
    query = (
        select(Event.product_id)
        .where(Event.type == "purchase", Event.product_id.not_in(bought))
        .group_by(Event.product_id)
        .order_by(desc(func.count()), Event.product_id)
        .limit(limit)
    )
    return list(db.scalars(query))


def evaluate(db, k=K):
    hidden, skipped = purchases_to_hide(db)
    recommender_hits = 0
    popular_hits = 0

    for user_id, (event_id, product_id) in hidden.items():
        # Delete the hidden purchase inside a transaction, so both methods only see the
        # remaining data, then roll back to put it back.
        db.execute(delete(Event).where(Event.id == event_id))
        recommended = [r["product"].id for r in recommend(db, user_id, k)]
        recommender_hits += product_id in recommended
        popular_hits += product_id in most_popular(db, user_id, k)
        db.rollback()

    return {
        "users": len(hidden),
        "skipped": skipped,
        "recommender": recommender_hits / len(hidden),
        "popular": popular_hits / len(hidden),
    }


def main():
    db = SessionLocal()
    result = evaluate(db)
    db.close()
    print(f"Users evaluated: {result['users']}")
    print(f"Users skipped (latest purchase was a repeat): {result['skipped']}")
    print(f"Recommender hit rate@{K}: {result['recommender']:.1%}")
    print(f"Popular baseline hit rate@{K}: {result['popular']:.1%}")


if __name__ == "__main__":
    main()
