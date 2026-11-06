import os
import random
from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Account, Event, Product, Segment, User

CATALOG = {
    "phones": ["Phone X", "Phone X Pro", "Phone Lite", "Phone Mini", "Phone Max"],
    "accessories": ["Phone Case", "Fast Charger", "USB-C Cable", "Screen Protector", "Power Bank"],
    "laptops": ["Laptop Air", "Laptop Pro 14", "Laptop Pro 16", "Gaming Laptop", "Chromebook"],
    "audio": ["Wireless Earbuds", "Over-Ear Headphones", "Bluetooth Speaker", "Soundbar", "Studio Mic"],
    "shoes": ["Running Shoes", "Trail Shoes", "Sneakers", "Boots", "Sandals"],
    "sportswear": ["Running Shorts", "Sports Bra", "Track Jacket", "Gym Shirt", "Compression Socks"],
    "home": ["Coffee Maker", "Air Fryer", "Blender", "Robot Vacuum", "Desk Lamp"],
    "books": ["Go in Practice", "Python Tricks", "Designing Data Apps", "Clean Code", "SQL Basics"],
}

# Categories people tend to shop together, so recommendations have something to find.
RELATED = {
    "phones": "accessories",
    "laptops": "audio",
    "shoes": "sportswear",
    "home": "books",
}

COUNTRIES = ["TR", "TR", "TR", "DE", "NL", "GB", "US"]

# The demo viewer is meant to be public: the login page shows it so anyone can look around.
DEMO_EMAIL = "demo@mini-cdp.dev"
DEMO_PASSWORD = "demo1234"


def main():
    random.seed(42)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    products_by_category = {}
    for category, names in CATALOG.items():
        products_by_category[category] = []
        for i, name in enumerate(names):
            product = Product(
                sku=f"{category[:3].upper()}-{i + 1:03}",
                name=name,
                category=category,
                price_cents=random.randint(5, 300) * 500,
            )
            db.add(product)
            products_by_category[category].append(product)
    db.flush()

    users = []
    for i in range(300):
        user = User(external_id=f"cust-{i + 1:04}", email=f"cust{i + 1}@example.com", country=random.choice(COUNTRIES))
        db.add(user)
        users.append(user)
    db.flush()

    events = []
    for user in users:
        main_category = random.choice(list(CATALOG))
        side_category = RELATED.get(main_category, random.choice(list(CATALOG)))
        # Some users stopped coming back a while ago.
        last_active_days = random.choice([0, 1, 3, 7, 14, 45, 70])

        for _ in range(random.randint(1, 8)):
            session_time = now - timedelta(days=last_active_days + random.randint(0, 60), minutes=random.randint(0, 1440))
            category = main_category if random.random() < 0.7 else side_category
            product = random.choice(products_by_category[category])

            events.append(Event(user_id=user.id, product_id=product.id, type="view", created_at=session_time))
            if random.random() < 0.4:
                events.append(
                    Event(user_id=user.id, product_id=product.id, type="add_to_cart", created_at=session_time + timedelta(minutes=2))
                )
                if random.random() < 0.6:
                    events.append(
                        Event(
                            user_id=user.id,
                            product_id=product.id,
                            type="purchase",
                            value_cents=product.price_cents,
                            created_at=session_time + timedelta(minutes=5),
                        )
                    )

    db.add_all(events)
    db.add_all(
        [
            Account(
                email=os.getenv("ADMIN_EMAIL", "admin@mini-cdp.dev"),
                password_hash=hash_password(os.environ["ADMIN_PASSWORD"]),
                role="admin",
            ),
            Account(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), role="viewer"),
        ]
    )
    db.add_all(
        [
            Segment(name="Big spenders", rules=[{"field": "total_spent_cents", "op": "gte", "value": 100000}]),
            Segment(
                name="Turkish repeat buyers",
                rules=[
                    {"field": "country", "op": "eq", "value": "TR"},
                    {"field": "purchase_count", "op": "gte", "value": 2},
                ],
            ),
            Segment(
                name="Win-back: browsed but inactive",
                rules=[
                    {"field": "days_since_last_event", "op": "gt", "value": 30},
                    {"field": "purchase_count", "op": "eq", "value": 0},
                ],
            ),
        ]
    )
    db.commit()
    print(f"Seeded {len(users)} users, {sum(len(p) for p in products_by_category.values())} products, {len(events)} events, 3 segments, 2 accounts")


if __name__ == "__main__":
    main()
