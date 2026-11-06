from datetime import datetime, time, timedelta, timezone

from sqlalchemy import case, desc, func, select

from app.models import Event, Product


def window_start(days):
    first_day = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    return first_day, datetime.combine(first_day, time.min, tzinfo=timezone.utc)


def daily(db, days):
    first_day, since = window_start(days)
    day = func.date(Event.created_at)
    rows = db.execute(
        select(day, func.count(), func.sum(Event.value_cents))
        .where(Event.created_at >= since)
        .group_by(day)
    )
    # Postgres returns dates and SQLite returns strings, so key both by "YYYY-MM-DD".
    totals = {str(d): (events, revenue) for d, events, revenue in rows}

    # Days without events have no row, so they are filled in with zeros here.
    result = []
    for i in range(days):
        d = first_day + timedelta(days=i)
        events, revenue = totals.get(d.isoformat(), (0, 0))
        result.append({"date": d, "events": events, "revenue_cents": revenue})
    return result


def did(event_type):
    return func.max(case((Event.type == event_type, 1), else_=0))


def rate(before, after):
    return round(after / before, 4) if before else None


def funnel(db, days):
    _, since = window_start(days)
    steps = (
        select(did("view").label("view"), did("add_to_cart").label("add_to_cart"), did("purchase").label("purchase"))
        .where(Event.created_at >= since)
        .group_by(Event.user_id)
        .subquery()
    )
    # A user only counts at a step if they also did every step before it. The order in
    # time doesn't matter, only that they did each one inside the window.
    reached_view = steps.c.view == 1
    reached_cart = reached_view & (steps.c.add_to_cart == 1)
    reached_purchase = reached_cart & (steps.c.purchase == 1)
    viewed, added_to_cart, purchased = db.execute(
        select(
            func.count(case((reached_view, 1))),
            func.count(case((reached_cart, 1))),
            func.count(case((reached_purchase, 1))),
        )
    ).one()
    return {
        "viewed": viewed,
        "added_to_cart": added_to_cart,
        "purchased": purchased,
        "view_to_cart_rate": rate(viewed, added_to_cart),
        "cart_to_purchase_rate": rate(added_to_cart, purchased),
    }


def top_products(db, days, limit):
    _, since = window_start(days)
    rows = db.execute(
        select(Product, func.count().label("purchases"), func.sum(Event.value_cents).label("revenue_cents"))
        .join(Event, Event.product_id == Product.id)
        .where(Event.type == "purchase", Event.created_at >= since)
        .group_by(Product.id)
        .order_by(desc("purchases"), desc("revenue_cents"), Product.id)
        .limit(limit)
    )
    return [{"product": product, "purchases": purchases, "revenue_cents": revenue} for product, purchases, revenue in rows]
