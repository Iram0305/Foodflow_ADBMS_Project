import json

import pandas as pd
import streamlit as st

from core import database
from core import dba
from core import shop
from core import spatial
from core import style
from core import temporal
from core import tracking


def timing(rows, ms):
    st.caption(style.number(rows) + " rows returned in " + str(round(ms, 1)) + " ms")


@st.dialog("Under the hood · Account", width="large")
def login(sql_text):
    tabs = st.tabs(["Create account", "Rules enforced by PostgreSQL", "Find existing account"])
    with tabs[0]:
        st.markdown("Creating an account is one INSERT. The new id is computed inside the statement itself, and `RETURNING` hands it straight back.")
        if sql_text:
            st.code(sql_text, language="sql")
        else:
            st.code(shop.CREATE_CUSTOMER_SQL, language="sql")
    with tabs[1]:
        st.markdown("The database, not the app, refuses bad data.")
        frame = database.fetch("""SELECT conname AS rule, CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK' END AS type,
                                         pg_get_constraintdef(oid) AS definition
                                  FROM pg_constraint WHERE conrelid = 'customer'::regclass AND contype IN ('p', 'u', 'c')""")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Try signing up with a phone number or email that already exists: the UNIQUE constraint rejects it.")
    with tabs[2]:
        sql = "SELECT customer_id, name, locality, phone\nFROM customer\nORDER BY name, customer_id;"
        st.code(sql, language="sql")
        st.caption("Every customer already in the database is listed in the sign-in box. Typing filters the list.")


@st.dialog("Under the hood · Restaurants near you", width="large")
def discover(sql_text, rows, ms, lat, lon):
    tabs = st.tabs(["Spatial query", "Nearest riders", "Why it is fast"])
    with tabs[0]:
        st.markdown("Distance from **your saved location** to every restaurant, filtered by delivery radius, joined with a pre-computed materialized view for popularity.")
        st.code(sql_text, language="sql")
        timing(rows, ms)
        st.caption("Spatial engine on this server: " + spatial.engine())
    with tabs[1]:
        partners, sql, elapsed = spatial.nearest_partners(lat, lon, 5)
        st.markdown("K-nearest-neighbour search: the 5 closest **available** delivery partners to you.")
        st.code(sql, language="sql")
        partners = partners.drop(columns=["latitude", "longitude"])
        st.dataframe(partners, hide_index=True, width="stretch")
    with tabs[2]:
        st.markdown("A bounding box on a B-tree index of `(latitude, longitude)` removes far-away rows before the exact distance is calculated. With PostGIS the same job is done by a GiST index and `ST_DWithin`.")
        indexes = database.fetch("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'restaurant'")
        st.dataframe(indexes, hide_index=True, width="stretch")


@st.dialog("Under the hood · Menu", width="large")
def menu(sql_text, rows, ms, restaurant_id):
    tabs = st.tabs(["Menu query", "Price history", "Stock control"])
    with tabs[0]:
        st.markdown("Items with a sub-query that counts how many times each dish was ordered (used for the Bestseller badge).")
        st.code(sql_text, language="sql")
        timing(rows, ms)
    with tabs[1]:
        items = database.fetch("SELECT item_id, item_name FROM menu_item WHERE restaurant_id = %s ORDER BY item_name", (int(restaurant_id),))
        labels = {}
        for row in items.to_dict("records"):
            labels[row["item_name"]] = int(row["item_id"])
        pick = st.selectbox("Dish", list(labels.keys()))
        history, elapsed = temporal.price_history(labels[pick])
        st.markdown("Temporal table: every price a dish has ever had, with the period it was valid. A trigger maintains it automatically whenever a price changes.")
        st.code(temporal.PRICE_HISTORY_SQL.strip(), language="sql")
        st.dataframe(history, hide_index=True, width="stretch")
    with tabs[2]:
        st.markdown("The number next to **Only N left** is the live `stock` column. When you pay, the order transaction locks the row with `SELECT ... FOR UPDATE` and re-checks it, so two people can never buy the last portion.")
        st.code("SELECT item_name, price, stock\nFROM menu_item\nWHERE item_id = 1001 AND restaurant_id = 3\nFOR UPDATE;\n\nUPDATE menu_item\nSET stock = stock - 1, version = version + 1\nWHERE item_id = 1001 AND stock >= 1;", language="sql")


@st.dialog("Under the hood · Payment transaction", width="large")
def checkout(result):
    tabs = st.tabs(["Transaction log", "ACID in plain words", "Template"])
    with tabs[0]:
        if result is None:
            st.info("Pay for an order first. The exact SQL of your transaction will appear here.")
        else:
            if result["outcome"] == "COMMITTED":
                style.banner("good", "✅", "COMMITTED · Order #" + str(result["order_id"]), "Every change was saved together.")
            else:
                style.banner("bad", "↩️", "ROLLED BACK · nothing was saved", result["reason"])
            style.steps(result["steps"])
            rows = []
            for item_id in result["before"]:
                rows.append({"item_id": item_id, "stock before": result["before"][item_id], "stock after": result["after"].get(item_id)})
            st.markdown("**Stock before and after**")
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with tabs[1]:
        st.markdown("**Atomicity:** stock reduction, order, order items, status history and payment either all happen or none do.")
        st.markdown("**Consistency:** CHECK, FOREIGN KEY and UNIQUE constraints are never violated, even if a step fails halfway.")
        st.markdown("**Isolation:** `FOR UPDATE` row locks stop another customer from buying the same last portion at the same time.")
        st.markdown("**Durability:** once `COMMIT` returns, the write-ahead log makes the order survive a crash.")
        st.caption("Tip: pay with card number 4000 0000 0000 0002 or a UPI id ending in @fail to watch a real ROLLBACK.")
    with tabs[2]:
        st.code("BEGIN;\n  SELECT ... FROM menu_item WHERE item_id = ? FOR UPDATE;\n  UPDATE menu_item SET stock = stock - ? WHERE item_id = ? AND stock >= ?;\n  INSERT INTO orders (...) VALUES (...) RETURNING order_id;\n  INSERT INTO order_item (...) VALUES (...);\n  INSERT INTO order_status_history (...) VALUES (...);\n  -- payment gateway call\n  INSERT INTO payment (...) VALUES (...);\nCOMMIT;   -- or ROLLBACK; if anything above fails", language="sql")


@st.dialog("Under the hood · Order tracking", width="large")
def tracking_view(order_id, info):
    tabs = st.tabs(["Status updates (PostgreSQL)", "Tracking document (MongoDB)", "Rider assignment", "Trigger"])
    with tabs[0]:
        st.markdown("Each status change is one `UPDATE`. A trigger writes the history row automatically.")
        st.code("UPDATE orders SET status = 'PREPARING' WHERE order_id = " + str(order_id) + ";", language="sql")
        history = shop.order_history(order_id)
        st.dataframe(history, hide_index=True, width="stretch")
    with tabs[1]:
        document = tracking.get_document(order_id)
        st.markdown("The same order as a MongoDB document: events are embedded in an array and the route is a GeoJSON LineString.")
        if document is None:
            st.info("No tracking document yet.")
        else:
            st.code(json.dumps(document, indent=2, default=str), language="json")
    with tabs[2]:
        partners, sql, elapsed = spatial.nearest_partners(info["r_lat"], info["r_lon"], 3)
        st.markdown("When the kitchen starts cooking, the nearest **available** rider to the restaurant is assigned using a spatial query:")
        st.code(sql, language="sql")
        st.dataframe(partners.drop(columns=["latitude", "longitude"]), hide_index=True, width="stretch")
    with tabs[3]:
        source = database.fetch_value("SELECT pg_get_functiondef('log_status_change'::regproc)")
        st.markdown("Trigger function that keeps the history table in sync:")
        st.code(source, language="sql")


@st.dialog("Under the hood · Your orders", width="large")
def my_orders(sql_text, customer_id):
    tabs = st.tabs(["Order history query", "Spending report"])
    with tabs[0]:
        st.markdown("Five tables joined, with a correlated sub-query that builds the item summary using `STRING_AGG`.")
        st.code(sql_text, language="sql")
    with tabs[1]:
        sql = """SELECT TO_CHAR(DATE_TRUNC('month', order_time), 'Mon YYYY') AS month,
       COUNT(*) AS orders,
       SUM(total_amount) AS spent,
       SUM(SUM(total_amount)) OVER (ORDER BY DATE_TRUNC('month', order_time)) AS running_total
FROM orders
WHERE customer_id = %(customer_id)s AND status = 'DELIVERED'
GROUP BY DATE_TRUNC('month', order_time)
ORDER BY DATE_TRUNC('month', order_time);"""
        st.markdown("Aggregation with a window function (running total):")
        st.code(database.render(sql, {"customer_id": int(customer_id)}), language="sql")
        frame, elapsed = database.run_query(sql, {"customer_id": int(customer_id)})
        st.dataframe(frame, hide_index=True, width="stretch")


@st.dialog("Under the hood · Account and security", width="large")
def account(customer_id, sql_text):
    tabs = st.tabs(["Update statement", "Row level security", "Rules"])
    with tabs[0]:
        if sql_text:
            st.code(sql_text, language="sql")
        else:
            st.code("UPDATE customer\nSET address = '...', locality = '...', latitude = ..., longitude = ...\nWHERE customer_id = " + str(customer_id) + ";", language="sql")
    with tabs[1]:
        st.markdown("Run as the `ff_customer` database role with `app.customer_id = " + str(customer_id) + "`. PostgreSQL itself filters the rows, so a customer can never read someone else's orders, even with a buggy app.")
        query = "SELECT order_id, customer_id, status, total_amount FROM orders ORDER BY order_time DESC LIMIT 10;"
        st.code("SET LOCAL ROLE ff_customer;\nSELECT set_config('app.customer_id', '" + str(customer_id) + "', true);\n" + query, language="sql")
        ok, frame, message = dba.run_as_role("ff_customer", query, customer_id)
        if ok and frame is not None:
            st.dataframe(frame, hide_index=True, width="stretch")
            st.caption("Distinct customer ids returned: " + str(sorted(frame["customer_id"].unique().tolist())))
        else:
            st.warning(message)
    with tabs[2]:
        frame = database.fetch("""SELECT conname AS rule, pg_get_constraintdef(oid) AS definition
                                  FROM pg_constraint WHERE conrelid = 'customer'::regclass AND contype IN ('p', 'u', 'c')""")
        st.dataframe(frame, hide_index=True, width="stretch")
