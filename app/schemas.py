from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    email: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)


class UserOut(UserIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str
    category: str
    price_cents: int = Field(ge=0)


class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EventIn(BaseModel):
    user_id: int
    product_id: int
    type: Literal["view", "add_to_cart", "purchase"]
    created_at: datetime | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: int
    type: str
    value_cents: int
    created_at: datetime


class Profile(BaseModel):
    user_id: int
    view_count: int
    add_to_cart_count: int
    purchase_count: int
    total_spent_cents: int
    last_event_at: datetime | None
    favorite_category: str | None


class Rule(BaseModel):
    field: Literal["country", "view_count", "purchase_count", "total_spent_cents", "days_since_last_event"]
    op: Literal["eq", "gt", "gte", "lt", "lte"]
    value: int | str

    @model_validator(mode="after")
    def check_value(self):
        if self.field == "country":
            if self.op != "eq" or not isinstance(self.value, str):
                raise ValueError("country only supports 'eq' with a country code")
        elif not isinstance(self.value, int):
            raise ValueError(f"{self.field} needs a number")
        if self.field == "days_since_last_event" and self.op == "eq":
            raise ValueError("days_since_last_event does not support 'eq'")
        return self


class SegmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rules: list[Rule] = Field(min_length=1)


class SegmentOut(SegmentIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SegmentPreviewIn(BaseModel):
    rules: list[Rule] = Field(min_length=1)


class SegmentPreview(BaseModel):
    count: int


class SegmentUsers(BaseModel):
    segment_id: int
    count: int
    users: list[UserOut]


class Recommendation(BaseModel):
    product: ProductOut
    score: int
    reason: Literal["bought_together", "popular"]


class DailyStats(BaseModel):
    date: date
    events: int
    revenue_cents: int


class Funnel(BaseModel):
    viewed: int
    added_to_cart: int
    purchased: int
    view_to_cart_rate: float | None
    cart_to_purchase_rate: float | None


class TopProduct(BaseModel):
    product: ProductOut
    purchases: int
    revenue_cents: int
