# Mini CDP

A small customer data platform backend. It collects user events from an online store (views, add to cart, purchases), builds a profile for each user, groups users into segments with simple rules, and recommends products based on what similar customers bought.

Built with Python, FastAPI, PostgreSQL, SQLAlchemy and pytest. Runs with Docker Compose, and GitHub Actions runs the tests against a real Postgres on every push.

## Run it

```bash
docker compose up --build
docker compose exec api python -m scripts.seed
```

The API is at http://localhost:8000, the interactive docs are at http://localhost:8000/docs and the dashboard is at http://localhost:5173.

The seed script creates 300 users, 40 products and a couple thousand events with realistic shopping habits (people who buy phones also tend to buy accessories, some users went inactive a month ago, and so on), plus three example segments. It also creates two dashboard accounts: an admin (`admin@mini-cdp.dev`, with the password from `ADMIN_PASSWORD`, which defaults to `admin-dev-password` in Docker Compose) and a demo viewer (`demo@mini-cdp.dev` / `demo1234`) that the login page offers with one click.

## Dashboard

A small Vue 3 app in `frontend/` that only uses the API above. The header has a user search that lists matching users as you type, with the same 300 ms wait as the segment preview. The home page is an overview of the last 7, 30 or 90 days: daily events and revenue as a line chart, the view → cart → purchase funnel with conversion rates, and the top products. The other pages show the segments with how many users are in each, the users in a segment (paged), a user page with the profile, recommendations and recent events, and a form to create or edit a segment from rules. The form shows how many users match while you change the rules: it waits until nothing has changed for 300 ms before calling the preview endpoint, so typing a number sends one request instead of one per keystroke. It is plain Vue with vue-router and no UI library, plus Chart.js for the line chart. Docker builds it and serves it with nginx. The API allows requests from the origins in `CORS_ORIGINS`, which defaults to `http://localhost:5173`, and the dashboard calls the API at `VITE_API_URL`, which defaults to `http://localhost:8000`.

To work on it with hot reload, run the API with Docker and start Vite on the same port:

```bash
cd frontend && npm install && npm run dev
```

## Deploy

The API runs on Render as a Docker web service, the dashboard as a Render static site, and Postgres on Neon. All three have free plans. `render.yaml` describes both Render services.

1. **Database.** Create a project on [Neon](https://neon.tech) and copy its connection string. Use the direct one, with connection pooling turned off. Neon's pooler doesn't get along with the prepared statements psycopg uses for repeated queries. The `postgresql://...` string can be pasted as it is: the app switches it to psycopg 3 itself.
2. **Render.** In the Render dashboard, choose New → Blueprint and pick this repository. Render asks for `DATABASE_URL`: paste the Neon string. It generates `JWT_SECRET` and `API_KEY` by itself.
3. **URLs.** `render.yaml` expects `https://mini-cdp-api.onrender.com` and `https://mini-cdp-dashboard.onrender.com`. If Render hands out different names, change `CORS_ORIGINS` on the API and `VITE_API_URL` on the dashboard to the real URLs, and redeploy the dashboard, because Vite builds the API URL into the files.
4. **Data.** The API creates the tables when it starts. Fill them once from your own machine. This drops and recreates every table, so only run it on a new database:

```bash
docker compose run --rm -e DATABASE_URL='<Neon connection string>' -e ADMIN_PASSWORD='<a long password>' api python -m scripts.seed
```

Settings, and where each one lives. Secrets never go in the repository:

| Name | Secret | Where | What it is |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | Render, API service | The Neon connection string |
| `JWT_SECRET` | yes | Render, API service, generated | Signs login tokens. Changing it logs everyone out |
| `API_KEY` | yes | Render, API service, generated | What the store sends as `X-API-Key`. Copy it from Render when you need it |
| `ADMIN_PASSWORD` | yes | Only your machine, when you run the seed | The admin account's password. The API never reads it |
| `CORS_ORIGINS` | no | `render.yaml` | The dashboard's URL, so the browser may call the API |
| `VITE_API_URL` | no | `render.yaml` | The API's URL, built into the dashboard |

On the free plan the API goes to sleep after 15 minutes without requests and takes about a minute to wake up, so the login page warns about it. Neon's free plan has no time limit, unlike Render's own free Postgres, which is deleted after 30 days.

## Run the tests

```bash
docker compose exec api pytest -v
```

Inside Docker the tests use a separate `cdp_test` database. Outside Docker, `pytest` falls back to SQLite so you can run it with no setup. Set `TEST_DATABASE_URL` to point it at any Postgres.

## Endpoints

Access: **viewer** means any logged-in account, **admin** means an admin account, and **store** means the `X-API-Key` header instead of a login.

| Method | Path | Access | What it does |
| --- | --- | --- | --- |
| GET | `/health` | open | Health check |
| POST | `/auth/login` | open | Log in with email and password, returns a token valid for 8 hours |
| POST | `/users` | store | Create a user |
| GET | `/users/search?q=&limit=20` | viewer | Users whose email or external id starts with `q`, ignoring case |
| GET | `/users/{id}` | viewer | Get a user |
| POST | `/products` | store | Create a product |
| GET | `/products?category=` | viewer | List products |
| POST | `/events` | store | Track one event |
| POST | `/events/batch` | store | Track up to 1000 events in one request |
| GET | `/users/{id}/events` | viewer | A user's latest events |
| GET | `/users/{id}/profile` | viewer | Counts, total spent, last activity, favorite category |
| GET | `/users/{id}/recommendations` | viewer | Recommended products |
| POST | `/segments` | admin | Create a segment from rules |
| POST | `/segments/preview` | viewer | Count the users that rules would match, without saving anything |
| PUT | `/segments/{id}` | admin | Change a segment's name and rules |
| DELETE | `/segments/{id}` | admin | Delete a segment |
| GET | `/segments` | viewer | List segments |
| GET | `/segments/{id}/users` | viewer | Users in a segment, with total count and paging |
| GET | `/analytics/daily?days=30` | viewer | Events and revenue per day, including days with no events |
| GET | `/analytics/funnel?days=30` | viewer | Users who viewed, then also added to cart, then also purchased, with conversion rates |
| GET | `/analytics/top-products?days=30&limit=10` | viewer | Products with the most purchases, then the most revenue |

The interactive docs at `/docs` stay open, and their Authorize button takes a token or an API key.

## Examples

Track a purchase, the way the store would, with the API key:

```bash
curl -X POST localhost:8000/events -H "content-type: application/json" -H "X-API-Key: dev-api-key" \
  -d '{"user_id": 7, "product_id": 3, "type": "purchase"}'
```

Log in as the admin and keep the token:

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H "content-type: application/json" \
  -d '{"email": "admin@mini-cdp.dev", "password": "admin-dev-password"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Create a win-back segment for users who browsed but never bought and have been gone for a month:

```bash
curl -X POST localhost:8000/segments -H "content-type: application/json" -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Win-back",
  "rules": [
    {"field": "days_since_last_event", "op": "gt", "value": 30},
    {"field": "purchase_count", "op": "eq", "value": 0}
  ]
}'
```

Rules can use `country`, `view_count`, `purchase_count`, `total_spent_cents` and `days_since_last_event`, with the operators `eq`, `gt`, `gte`, `lt` and `lte`. All rules in a segment must match. Invalid rules are rejected with a 422.

## How it works

**Login and roles.** Dashboard accounts live in their own `accounts` table, separate from `users`, which are the store's customers. Passwords are hashed with bcrypt, which is slow on purpose and salts each hash, so a leaked table can't be reversed with precomputed tables. `POST /auth/login` returns a JWT signed with `JWT_SECRET` that holds the account id and role and expires after 8 hours. The API doesn't keep sessions: it checks the signature and expiry on every request. The flip side is that a token can't be revoked early, and a role change only takes effect at the next login. Every route sits in one of three routers whose dependency does the check, so a route's decorator (`@viewer`, `@admin` or `@store`) shows who may call it. A missing or bad token gets a 401, and a viewer trying to change a segment gets a 403.

The store's endpoints use an API key instead, because they are called by another server, not a person. The key is compared with `secrets.compare_digest`, which takes the same time however much of the key matches, so it can't be guessed one character at a time by timing responses.

The dashboard hides the create, edit and delete controls from viewers and keeps them off admin-only pages, but that is only for convenience. Anyone can call the API without the dashboard, so the API checks the role on every request itself. The dashboard keeps the token in memory and in `sessionStorage`, so a reload keeps you logged in and closing the tab logs you out. Any script running on the page could read `sessionStorage`. An `HttpOnly` cookie would avoid that, but it brings CSRF protection to think about, so it is left for later.

**Profiles and segments are computed with SQL.** A segment is turned into one query. It joins users to an aggregated view of their events (counts, sum of spend, last event time) and adds a `WHERE` condition per rule. Nothing is loaded into Python and filtered there, so it stays fast as the events table grows.

**Recommendations** look at other users who bought something this user bought, and count what else those users bought. Products are ranked by how many different users bought them, and anything the user already owns is left out. If that gives fewer results than asked for, the rest is filled with the most purchased products of the last 30 days, so new users still get something.

**Money is stored as integer cents** to avoid rounding errors. A purchase event copies the product's price at the time of purchase, so later price changes don't rewrite past revenue.

**Indexes** on `events(user_id, created_at)` and `events(type, product_id)` match the two main access patterns, reading one user's history and counting purchases per product.

**Analytics are grouped in SQL.** Each endpoint is one `GROUP BY` query over the events of the last N days, counted from the start of the first day in UTC. Days without events have no row in the result, so the daily endpoint fills them in with zeros afterwards. The funnel is strict: a user counts at a step only if they also did every step before it in the window, in any order, so conversion rates never go over 100%. A conversion rate is `null` when the step before it has no users.

**User search uses prefix indexes.** The search runs `lower(email) LIKE 'ali%'` (and the same for `external_id`), and each has an index on `lower(...)` built with `text_pattern_ops`. A B-tree index keeps values in sorted order, so every value that starts with `ali` sits in one block between `ali` and `alj`. Postgres jumps to the start of that block and reads until the end of it, which `EXPLAIN` shows as `Index Cond: lower(email) ~>=~ 'ali' AND lower(email) ~<~ 'alj'`. A "contains" search like `'%ali%'` can match anywhere in the string, so the sorted order doesn't help: there is no place in the index to start from, and Postgres has to read every row. That would need a different kind of index, such as a trigram index from `pg_trgm`. The `text_pattern_ops` part is needed because the database sorts text by language rules by default, and those rules don't guarantee that strings with the same prefix sit next to each other. `text_pattern_ops` sorts by plain character codes, where they do. The indexes are on `lower(...)` because the query searches on `lower(...)`, and an index on the plain column wouldn't match it.

Tables are created on startup and `create_all` doesn't add new indexes to tables that already exist. On an existing database, run the seed script again, or create the two indexes by hand from `app/models.py`.

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
  auth.py             tokens, roles and the API key check
  passwords.py        bcrypt hashing
scripts/seed.py       demo data
scripts/evaluate.py   recommender hit rate vs. a popular baseline
render.yaml           Render services for the API and the dashboard
frontend/             Vue dashboard
tests/                pytest suite
```

## What I would add next

Migrations with Alembic instead of creating tables on startup, an API key per client, and moving event ingestion to a queue so tracking requests return immediately.
