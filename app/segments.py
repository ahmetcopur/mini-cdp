import operator
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select

from app.models import Event, User

OPS = {
    "eq": operator.eq,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}

# "more than N days since last event" means "last event is older than now - N days",
# so the comparison on the timestamp goes the other way.
FLIPPED = {"gt": "lt", "gte": "lte", "lt": "gt", "lte": "gte"}


def profile_table():
    return (
        select(
            User.id.label("user_id"),
            User.country.label("country"),
            func.count(case((Event.type == "view", 1))).label("view_count"),
            func.count(case((Event.type == "purchase", 1))).label("purchase_count"),
            func.coalesce(func.sum(Event.value_cents), 0).label("total_spent_cents"),
            func.max(Event.created_at).label("last_event_at"),
        )
        .outerjoin(Event, Event.user_id == User.id)
        .group_by(User.id, User.country)
        .subquery()
    )


def segment_query(rules):
    profiles = profile_table()
    query = select(User).join(profiles, profiles.c.user_id == User.id)
    now = datetime.now(timezone.utc)

    for rule in rules:
        if rule["field"] == "days_since_last_event":
            cutoff = now - timedelta(days=rule["value"])
            compare = OPS[FLIPPED[rule["op"]]]
            query = query.where(compare(profiles.c.last_event_at, cutoff))
        else:
            compare = OPS[rule["op"]]
            query = query.where(compare(profiles.c[rule["field"]], rule["value"]))

    return query.order_by(User.id)
