from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import aliased

from app.models import Event, Product


def recommend(db, user_id, limit):
    bought = select(Event.product_id).where(Event.user_id == user_id, Event.type == "purchase")

    # Other users who bought something this user bought: what else did they buy?
    mine = aliased(Event)
    theirs = aliased(Event)
    bought_together = (
        select(theirs.product_id, func.count(func.distinct(theirs.user_id)).label("score"))
        .select_from(mine)
        .join(theirs, theirs.user_id == mine.user_id)
        .where(
            mine.type == "purchase",
            mine.product_id.in_(bought),
            mine.user_id != user_id,
            theirs.type == "purchase",
            theirs.product_id.not_in(bought),
        )
        .group_by(theirs.product_id)
        .order_by(desc("score"), theirs.product_id)
        .limit(limit)
    )
    results = [(product_id, score, "bought_together") for product_id, score in db.execute(bought_together)]

    # Fill the rest with the most purchased products of the last 30 days.
    if len(results) < limit:
        already = [product_id for product_id, _, _ in results]
        since = datetime.now(timezone.utc) - timedelta(days=30)
        popular = (
            select(Event.product_id, func.count().label("score"))
            .where(
                Event.type == "purchase",
                Event.created_at >= since,
                Event.product_id.not_in(bought),
                Event.product_id.not_in(already),
            )
            .group_by(Event.product_id)
            .order_by(desc("score"), Event.product_id)
            .limit(limit - len(results))
        )
        results += [(product_id, score, "popular") for product_id, score in db.execute(popular)]

    products = db.scalars(select(Product).where(Product.id.in_([r[0] for r in results])))
    by_id = {p.id: p for p in products}
    return [{"product": by_id[pid], "score": score, "reason": reason} for pid, score, reason in results]
