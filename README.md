# FoodFlow — An Advanced Hybrid Database Management System for Food Delivery

ADBMS mini project. PostgreSQL is the system of record for customers, restaurants, menus, orders, payments and deliveries. MongoDB stores the order tracking event stream. A Streamlit app demonstrates every advanced DBMS concept live.

## What it demonstrates

| Rubric component | Where in the app |
|---|---|
| Dataset & real-world problem | Dataset & Design: problem statement, generation method, ~1.6 lakh rows over 11 tables, sample rows, CSV downloads |
| Database design | Dataset & Design: live ER diagram, every PK / FK / UNIQUE / CHECK, normalization, triggers |
| Transactions (ACID) | Place Order: full order in one transaction with injectable failures and ROLLBACK |
| Concurrency control | Concurrency Lab: lost update vs FOR UPDATE vs optimistic versioning vs SERIALIZABLE, plus deadlock detection |
| NoSQL | Live Tracking: MongoDB documents with embedded events and GeoJSON routes, aggregation pipelines |
| Spatial (GIS) | Delivery Map: radius search, KNN nearest rider, coverage spatial join, 3D density map |
| Temporal | Temporal Data: valid-time price history kept by a trigger, time-travel menu, lifecycle durations |
| Queries & evidence | Query Lab: 16 categorized queries with SQL, output, timing and charts, plus a read-only SQL console |
| DBA | DBA Console: roles + row level security, EXPLAIN ANALYZE before/after index, backup → disaster → restore, monitoring |

## Project structure

```
foodflow/
├── app.py                     Streamlit entry point and navigation
├── build.py                   Builds the database from the CSV dataset
├── requirements.txt
├── docker-compose.yml         PostgreSQL + PostGIS and MongoDB
├── .env.example
├── assets/                    Logo files
├── core/                      Backend logic
│   ├── config.py              Connection settings (.env or Streamlit secrets)
│   ├── database.py            PostgreSQL helpers
│   ├── generator.py           Synthetic Mumbai dataset generator
│   ├── loader.py              Schema creation, CSV loading, PostGIS, security
│   ├── orders.py              Order transaction, status changes, cancellation
│   ├── concurrency.py         Race and deadlock simulations
│   ├── tracking.py            MongoDB documents and aggregation pipelines
│   ├── spatial.py             Spatial queries (PostGIS or haversine)
│   ├── temporal.py            Temporal queries
│   ├── queries.py             Query Lab library
│   ├── dba.py                 Security, indexing, backup, monitoring
│   └── style.py               Theme and UI components
├── views/                     One file per page
├── sql/                       schema, functions/triggers, indexes, PostGIS, security
└── data/                      The dataset as CSV files
```

## Run locally

Requirements: Python 3.10+, and either Docker Desktop or your own PostgreSQL (MongoDB optional).

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

docker compose up -d           # starts PostgreSQL + PostGIS and MongoDB
python build.py                # creates and loads the database (or use the button in the app)
streamlit run app.py
```

Without Docker, install PostgreSQL, create a database called `foodflow`, copy `.env.example` to `.env` and set your password in `DATABASE_URL`. If MongoDB is not running the app automatically falls back to an in-memory MongoDB engine, and if PostGIS is not installed it uses a haversine SQL function instead.

## Deploy on Streamlit Community Cloud

1. Create a free PostgreSQL database on Supabase or Neon (both include PostGIS) and a free MongoDB Atlas cluster.
2. Push this repository to GitHub.
3. On share.streamlit.io create an app from the repo with `app.py` as the main file.
4. In the app's Secrets, paste the contents of `.streamlit/secrets.toml.example` with your real connection strings.
5. Open the app and press **Build the database now** once.

## Dataset

Synthetic dataset generated for academic experimentation based on real-world food delivery workflows. 25 real Mumbai localities, 120 restaurants across 12 cuisines, 1,500 customers, 150 delivery partners and 15,000 orders over 180 days with realistic meal-time peaks, distance-based restaurant choice, payment failures, cancellations, refunds and price changes. Regenerate with `python build.py --regenerate`.
