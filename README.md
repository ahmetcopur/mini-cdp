# Mini CDP

A small customer data platform backend. It collects user events from an online store (views, add to cart, purchases), builds a profile for each user, groups users into segments with simple rules, and recommends products based on what similar customers bought.

Built with Python, FastAPI, PostgreSQL, SQLAlchemy and pytest. Runs with Docker Compose, and GitHub Actions runs the tests against a real Postgres on every push.

## Run it

```bash
docker compose up --build
docker compose exec api python -m scripts.seed
```

The API is at http://localhost:8000, the interactive docs are at http://localhost:8000/docs and the dashboard is at http://localhost:5173.

The seed script creates 300 users, 40 products and a couple thousand events with realistic shopping habits (people who buy phones also tend to buy accessories, some users went inactive a month ago, and so on), plus three example segments.

## Dashboard

A small Vue 3 app in `frontend/` that only uses the API above. The home page is an overview of the last 7, 30 or 90 days: daily events and revenue as a line chart, the view → cart → purchase funnel with conversion rates, and the top products. The other pages show the segments with how many users are in each, the users in a segment (paged), a user page with the profile, recommendations and recent events, and a form to create or edit a segment from rules. The form shows how many users match while you change the rules: it waits until nothing has changed for 300 ms before calling the preview endpoint, so typing a number sends one request instead of one per keystroke. It is plain Vue with vue-router and no UI library, plus Chart.js for the line chart. Docker builds it and serves it with nginx. The API allows requests from `http://localhost:5173` through CORS.

To work on it with hot reload, run the API with Docker and start Vite on the same port:

```bash
cd frontend && npm install && npm run dev
```

## Run the tests

```bash
docker compose exec api pytest -v
```

Inside Docker the tests use a separate `cdp_test` database. Outside Docker, `pytest` falls back to SQLite so you can run it with no setup. Set `TEST_DATABASE_URL` to point it at any Postgres.

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/users` | Create a user |
| GET | `/users/{id}` | Get a user |
| POST | `/products` | Create a product |
| GET | `/products?category=` | List products |
| POST | `/events` | Track one event |
| POST | `/events/batch` | Track up to 1000 events in one request |
| GET | `/users/{id}/events` | A user's latest events |
| GET | `/users/{id}/profile` | Counts, total spent, last activity, favorite category |
| GET | `/users/{id}/recommendations` | Recommended products |
| POST | `/segments` | Create a segment from rules |
| POST | `/segments/preview` | Count the users that rules would match, without saving anything |
| PUT | `/segments/{id}` | Change a segment's name and rules |
| DELETE | `/segments/{id}` | Delete a segment |
| GET | `/segments` | List segments |
| GET | `/segments/{id}/users` | Users in a segment, with total count and paging |
| GET | `/analytics/daily?days=30` | Events and revenue per day, including days with no events |
| GET | `/analytics/funnel?days=30` | Users who viewed, then also added to cart, then also purchased, with conversion rates |
| GET | `/analytics/top-products?days=30&limit=10` | Products with the most purchases, then the most revenue |

## Examples

Track a purchase:

```bash
curl -X POST localhost:8000/events -H "content-type: application/json" \
  -d '{"user_id": 7, "product_id": 3, "type": "purchase"}'
```

Create a win-back segment for users who browsed but never bought and have been gone for a month:

```bash
curl -X POST localhost:8000/segments -H "content-type: application/json" -d '{
  "name": "Win-back",
  "rules": [
    {"field": "days_since_last_event", "op": "gt", "value": 30},
    {"field": "purchase_count", "op": "eq", "value": 0}
  ]
}'
```

Rules can use `country`, `view_count`, `purchase_count`, `total_spent_cents` and `days_since_last_event`, with the operators `eq`, `gt`, `gte`, `lt` and `lte`. All rules in a segment must match. Invalid rules are rejected with a 422.

## How it works

**Profiles and segments are computed with SQL.** A segment is turned into one query. It joins users to an aggregated view of their events (counts, sum of spend, last event time) and adds a `WHERE` condition per rule. Nothing is loaded into Python and filtered there, so it stays fast as the events table grows.

**Recommendations** look at other users who bought something this user bought, and count what else those users bought. Products are ranked by how many different users bought them, and anything the user already owns is left out. If that gives fewer results than asked for, the rest is filled with the most purchased products of the last 30 days, so new users still get something.

**Money is stored as integer cents** to avoid rounding errors. A purchase event copies the product's price at the time of purchase, so later price changes don't rewrite past revenue.

**Indexes** on `events(user_id, created_at)` and `events(type, product_id)` match the two main access patterns, reading one user's history and counting purchases per product.

**Analytics are grouped in SQL.** Each endpoint is one `GROUP BY` query over the events of the last N days, counted from the start of the first day in UTC. Days without events have no row in the result, so the daily endpoint fills them in with zeros afterwards. The funnel is strict: a user counts at a step only if they also did every step before it in the window, in any order, so conversion rates never go over 100%. A conversion rate is `null` when the step before it has no users.

**Batch inserts are all or nothing.** If any event in a batch points to an unknown user or product, the request fails and nothing is saved.

## Evaluating recommendations

```bash
docker compose exec api python -m scripts.evaluate
```

The script takes every user with at least 2 purchases and hides their latest purchase. It then asks for 5 recommendations using only the remaining data and checks if the hidden product is among them. The hit rate@5 is the share of users where it is. The hidden purchase is deleted inside a transaction and rolled back afterwards, so the real recommender code runs unchanged and the database is left as it was.

The baseline recommends the 5 most purchased products the user doesn't own yet. The recommender never suggests products the user already owns either, so a hidden purchase of something they bought before can never be a hit. Those users are skipped and counted separately.

Results on the seed data:

| | Hit rate@5 |
| --- | --- |
| Recommender (bought together) | 37.7% |
| Baseline (most popular) | 18.2% |

77 users were evaluated and 12 were skipped because their latest purchase was a repeat.

## Project layout

```
app/
  main.py             routes
  models.py           database tables
  schemas.py          request and response models, rule validation
  profiles.py         user profile queries
  segments.py         turns segment rules into a SQL query
  recommendations.py  bought-together and popular queries
  analytics.py        daily, funnel and top product queries
scripts/seed.py       demo data
scripts/evaluate.py   recommender hit rate vs. a popular baseline
frontend/             Vue dashboard
tests/                pytest suite
```

## What I would add next

Migrations with Alembic instead of creating tables on startup, an API key per client, and moving event ingestion to a queue so tracking requests return immediately.
