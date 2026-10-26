import pandas as pd
import plotly.express as px
import streamlit as st

from core import database
from core import style
from core import tracking

TILES_PG = [("11 tables", "PK · FK · CHECK · UNIQUE"), ("ACID", "row locks · isolation"), ("Spatial", "PostGIS / haversine"),
            ("Temporal", "valid-time history"), ("Security", "roles · RLS"), ("DBA", "indexes · backup · stats")]
TILES_MG = [("order_tracking", "one document per order"), ("Embedded events", "array grows with $push"), ("Pipelines", "$unwind · $group · $filter")]


def tiles(items):
    text = '<div class="ff-arch-tiles">'
    for title, sub in items:
        text = text + '<div class="ff-arch-tile"><b>' + title + "</b>" + sub + "</div>"
    return text + "</div>"


def architecture():
    return ('<div class="ff-arch">'
            '<div class="ff-arch-box ff-arch-dark"><b>Streamlit UI</b><div class="ff-arch-small">9 interactive modules for customers, staff and the DBA</div></div>'
            '<div class="ff-arch-arrow">→</div>'
            '<div class="ff-arch-box ff-arch-light"><b>Python service layer</b><div class="ff-arch-small">psycopg2 for SQL, pymongo for documents. '
            'Writes go to PostgreSQL first, then the order document is re-synced to MongoDB after COMMIT.</div></div>'
            '<div class="ff-arch-arrow">→</div>'
            '<div class="ff-arch-stores">'
            '<div class="ff-arch-store ff-arch-pg"><div class="ff-arch-title" style="color:#E8532B">PostgreSQL · system of record</div>' + tiles(TILES_PG) + '</div>'
            '<div class="ff-arch-store ff-arch-mg"><div class="ff-arch-title" style="color:#2A9D8F">MongoDB · event store</div>' + tiles(TILES_MG) + '</div>'
            '</div></div>')


RUBRIC = [
    ("Dataset & real-world problem", "1.5", "Dataset & Design", "Problem statement, generation method, 1.6 lakh rows across 11 tables, sample rows, CSV downloads"),
    ("Database design", "2", "Dataset & Design", "ER diagram, live schema browser with every PK/FK/CHECK/UNIQUE, normalization to 3NF"),
    ("ADBMS core implementation", "3", "Place Order · Concurrency · Tracking · Map · Temporal", "ACID with rollback, 4 concurrency strategies + deadlock, MongoDB events, spatial search, valid-time history"),
    ("Queries & evidence", "1.5", "Query Lab", "16 categorized queries with SQL, live output, execution time and charts, plus a read-only SQL console"),
    ("DBA responsibilities", "1", "DBA Console", "Roles + row level security, EXPLAIN ANALYZE before/after index, backup / disaster / restore, monitoring"),
]


def show():
    style.hero("ADBMS mini project · Food delivery",
               "FoodFlow: a hybrid database for food delivery",
               "Orders, payments and inventory live in PostgreSQL with full ACID guarantees. Every status change is also streamed into MongoDB as a flexible event document. "
               "Location search runs as spatial queries and price changes are kept as temporal history.",
               ["PostgreSQL", "MongoDB", "Spatial (GIS)", "Temporal", "Transactions", "Concurrency control", "Security & RLS", "Backup & recovery"])

    numbers = database.fetch("""
        SELECT (SELECT COUNT(*) FROM orders) AS orders,
               (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'DELIVERED') AS revenue,
               (SELECT COUNT(*) FROM restaurant) AS restaurants,
               (SELECT COUNT(*) FROM customer) AS customers,
               (SELECT COUNT(*) FROM delivery_partner) AS partners,
               (SELECT ROUND(AVG(EXTRACT(EPOCH FROM (d.delivered_time - o.order_time)) / 60)::numeric, 1)
                  FROM orders o JOIN delivery d ON d.order_id = o.order_id WHERE d.delivered_time IS NOT NULL) AS avg_minutes
    """).iloc[0]
    stats = tracking.document_stats()

    style.kpis([
        ("Orders", style.number(numbers["orders"]), "last 180 days"),
        ("Delivered revenue", style.money(numbers["revenue"]), "GMV across Mumbai"),
        ("Restaurants", style.number(numbers["restaurants"]), style.number(numbers["customers"]) + " customers"),
        ("Avg delivery", str(numbers["avg_minutes"]) + " min", "order to doorstep"),
        ("Live orders", style.number(stats["live"]), style.number(stats["documents"]) + " Mongo docs"),
    ])

    style.section("01", "System architecture", "Each kind of data goes to the engine that suits it best. PostgreSQL is the source of truth, MongoDB holds the high-volume, semi-structured tracking events.")
    st.markdown(architecture(), unsafe_allow_html=True)

    style.section("02", "Business at a glance")
    left, right = st.columns([3, 2])
    daily = database.fetch("""
        SELECT DATE(order_time) AS day, COUNT(*) AS orders,
               SUM(total_amount) FILTER (WHERE status = 'DELIVERED') AS revenue
        FROM orders GROUP BY 1 ORDER BY 1
    """)
    figure = px.area(daily, x="day", y="orders", title="Orders per day")
    figure.update_traces(line_color=style.ORANGE, fillcolor="rgba(232,83,43,0.15)")
    figure.update_layout(height=320, xaxis_title=None, yaxis_title=None)
    left.plotly_chart(figure, width="stretch")

    cuisine = database.fetch("""
        SELECT r.cuisine, SUM(o.total_amount) AS revenue
        FROM orders o JOIN restaurant r ON r.restaurant_id = o.restaurant_id
        WHERE o.status = 'DELIVERED' GROUP BY 1 ORDER BY 2 DESC
    """)
    figure = px.pie(cuisine, names="cuisine", values="revenue", hole=0.62, title="Revenue share by cuisine")
    figure.update_traces(textposition="inside", textinfo="percent")
    figure.update_layout(height=320, showlegend=True, legend=dict(font=dict(size=11)))
    right.plotly_chart(figure, width="stretch")

    left, right = st.columns([2, 3])
    status = database.fetch("SELECT status, COUNT(*) AS orders FROM orders GROUP BY 1 ORDER BY 2 DESC")
    figure = px.bar(status, x="orders", y="status", orientation="h", title="Orders by status", text="orders")
    figure.update_traces(marker_color=style.INK)
    figure.update_layout(height=300, xaxis_type="log", yaxis_title=None, xaxis_title=None)
    left.plotly_chart(figure, width="stretch")

    live = database.fetch("""
        SELECT o.order_id, c.name AS customer, r.name AS restaurant, o.status,
               TO_CHAR(o.order_time, 'HH24:MI') AS placed, o.total_amount
        FROM orders o
        JOIN customer c ON c.customer_id = o.customer_id
        JOIN restaurant r ON r.restaurant_id = o.restaurant_id
        WHERE o.status NOT IN ('DELIVERED', 'CANCELLED')
        ORDER BY o.order_time DESC LIMIT 8
    """)
    right.markdown("**Orders in progress right now**")
    right.dataframe(live, hide_index=True, width="stretch", height=280)

    style.section("03", "Where each rubric component is demonstrated", "A quick map for the evaluator.")
    html_parts = ['<div class="ff-rubric"><div class="ff-rh">Marks</div><div class="ff-rh">Component</div><div class="ff-rh">Where</div><div class="ff-rh">Evidence inside the app</div>']
    for component, marks, page, evidence in RUBRIC:
        html_parts.append('<div class="ff-rm">' + marks + "</div><div><b>" + component + "</b></div><div>" + page + "</div><div>" + evidence + "</div>")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    style.footer()
