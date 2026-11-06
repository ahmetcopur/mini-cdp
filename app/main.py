from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics
from app.database import Base, engine, get_db
from app.models import Event, Product, Segment, User
from app.profiles import build_profile
from app.recommendations import recommend
from app.schemas import (
    DailyStats,
    EventIn,
    EventOut,
    Funnel,
    ProductIn,
    ProductOut,
    Profile,
    Recommendation,
    SegmentIn,
    SegmentOut,
    SegmentPreview,
    SegmentPreviewIn,
    SegmentUsers,
    TopProduct,
    UserIn,
    UserOut,
)
from app.segments import count_users, segment_query


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Mini CDP", lifespan=lifespan)
# The dashboard runs on its own port, so the browser needs permission to call the API.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def get_user_or_404(db, user_id):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def get_segment_or_404(db, segment_id):
    segment = db.get(Segment, segment_id)
    if segment is None:
        raise HTTPException(404, "Segment not found")
    return segment


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.external_id == body.external_id)):
        raise HTTPException(409, "external_id already exists")
    user = User(**body.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.sku == body.sku)):
        raise HTTPException(409, "sku already exists")
    product = Product(**body.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=list[ProductOut])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    query = select(Product).order_by(Product.id)
    if category:
        query = query.where(Product.category == category)
    return db.scalars(query).all()


def make_events(db, items):
    user_ids = {item.user_id for item in items}
    product_ids = {item.product_id for item in items}

    found_users = set(db.scalars(select(User.id).where(User.id.in_(user_ids))))
    if found_users != user_ids:
        raise HTTPException(404, f"Unknown user ids: {sorted(user_ids - found_users)}")

    prices = dict(db.execute(select(Product.id, Product.price_cents).where(Product.id.in_(product_ids))).all())
    if set(prices) != product_ids:
        raise HTTPException(404, f"Unknown product ids: {sorted(product_ids - set(prices))}")

    events = []
    for item in items:
        event = Event(user_id=item.user_id, product_id=item.product_id, type=item.type)
        if item.type == "purchase":
            event.value_cents = prices[item.product_id]
        if item.created_at:
            event.created_at = item.created_at
        events.append(event)
    return events


@app.post("/events", response_model=EventOut, status_code=201)
def create_event(body: EventIn, db: Session = Depends(get_db)):
    event = make_events(db, [body])[0]
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.post("/events/batch", status_code=201)
def create_events(body: list[EventIn], db: Session = Depends(get_db)):
    if not 1 <= len(body) <= 1000:
        raise HTTPException(422, "Send between 1 and 1000 events")
    db.add_all(make_events(db, body))
    db.commit()
    return {"inserted": len(body)}


@app.get("/users/{user_id}/events", response_model=list[EventOut])
def list_user_events(user_id: int, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    query = (
        select(Event)
        .where(Event.user_id == user_id)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .limit(limit)
    )
    return db.scalars(query).all()


@app.get("/users/{user_id}/profile", response_model=Profile)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    return build_profile(db, user_id)


@app.get("/users/{user_id}/recommendations", response_model=list[Recommendation])
def get_recommendations(user_id: int, limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    return recommend(db, user_id, limit)


@app.post("/segments", response_model=SegmentOut, status_code=201)
def create_segment(body: SegmentIn, db: Session = Depends(get_db)):
    if db.scalar(select(Segment).where(Segment.name == body.name)):
        raise HTTPException(409, "Segment name already exists")
    segment = Segment(name=body.name, rules=[rule.model_dump() for rule in body.rules])
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


@app.post("/segments/preview", response_model=SegmentPreview)
def preview_segment(body: SegmentPreviewIn, db: Session = Depends(get_db)):
    return {"count": count_users(db, [rule.model_dump() for rule in body.rules])}


@app.put("/segments/{segment_id}", response_model=SegmentOut)
def update_segment(segment_id: int, body: SegmentIn, db: Session = Depends(get_db)):
    segment = get_segment_or_404(db, segment_id)
    if db.scalar(select(Segment).where(Segment.name == body.name, Segment.id != segment_id)):
        raise HTTPException(409, "Segment name already exists")
    segment.name = body.name
    segment.rules = [rule.model_dump() for rule in body.rules]
    db.commit()
    db.refresh(segment)
    return segment


@app.delete("/segments/{segment_id}", status_code=204)
def delete_segment(segment_id: int, db: Session = Depends(get_db)):
    db.delete(get_segment_or_404(db, segment_id))
    db.commit()


@app.get("/segments", response_model=list[SegmentOut])
def list_segments(db: Session = Depends(get_db)):
    return db.scalars(select(Segment).order_by(Segment.id)).all()


@app.get("/segments/{segment_id}/users", response_model=SegmentUsers)
def get_segment_users(
    segment_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    segment = get_segment_or_404(db, segment_id)
    users = db.scalars(segment_query(segment.rules).limit(limit).offset(offset)).all()
    return {"segment_id": segment_id, "count": count_users(db, segment.rules), "users": users}


@app.get("/analytics/daily", response_model=list[DailyStats])
def get_daily(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    return analytics.daily(db, days)


@app.get("/analytics/funnel", response_model=Funnel)
def get_funnel(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    return analytics.funnel(db, days)


@app.get("/analytics/top-products", response_model=list[TopProduct])
def get_top_products(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return analytics.top_products(db, days, limit)
