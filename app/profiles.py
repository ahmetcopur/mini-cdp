from sqlalchemy import desc, func, select

from app.models import Event, Product


def build_profile(db, user_id):
    counts = {"view": 0, "add_to_cart": 0, "purchase": 0}
    total_spent = 0

    rows = db.execute(
        select(Event.type, func.count(), func.sum(Event.value_cents))
        .where(Event.user_id == user_id)
        .group_by(Event.type)
    ).all()
    for event_type, count, value in rows:
        counts[event_type] = count
        total_spent += value or 0

    last_event_at = db.scalar(select(func.max(Event.created_at)).where(Event.user_id == user_id))

    favorite = db.execute(
        select(Product.category, func.count().label("n"))
        .join(Event, Event.product_id == Product.id)
        .where(Event.user_id == user_id)
        .group_by(Product.category)
        .order_by(desc("n"), Product.category)
        .limit(1)
    ).first()

    return {
        "user_id": user_id,
        "view_count": counts["view"],
        "add_to_cart_count": counts["add_to_cart"],
        "purchase_count": counts["purchase"],
        "total_spent_cents": total_spent,
        "last_event_at": last_event_at,
        "favorite_category": favorite[0] if favorite else None,
    }
