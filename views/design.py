import os

import pandas as pd
import plotly.express as px
import streamlit as st

from core import config
from core import database
from core import style

TABLES = ["customer", "restaurant", "menu_item", "menu_price_history", "delivery_partner", "orders",
          "order_item", "order_status_history", "payment", "delivery", "review"]

TABLE_NOTES = {
    "customer": "People who order food, with a home location",
    "restaurant": "Restaurant outlets with cuisine, rating and coordinates",
    "menu_item": "Dishes with current price, live stock and a version number",
    "menu_price_history": "Valid-time history of every price a dish ever had",
    "delivery_partner": "Riders with vehicle, availability and live location",
    "orders": "One row per order, the heart of the system",
    "order_item": "Which dishes, how many, at what price (M:N resolver)",
    "order_status_history": "Every status change with its timestamp",
    "payment": "Exactly one payment attempt per order",
    "delivery": "Partner assignment, pickup and drop times, distance",
    "review": "Star rating and comment for a delivered order",
}

NORMAL_FORMS = [
    ("1NF", "Every column holds one atomic value. Order lines live in order_item instead of a comma separated list inside orders."),
    ("2NF", "order_item has the composite key (order_id, item_id) and every other column depends on the whole key, not just part of it."),
    ("3NF", "No transitive dependencies: restaurant name and cuisine are stored once in restaurant, not repeated on every order."),
    ("BCNF", "Every determinant is a candidate key. Natural keys such as phone and email are declared UNIQUE."),
]


def er_diagram():
    columns = database.fetch("""
        SELECT table_name, column_name, data_type, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY(%s) AND column_name <> 'geom'
        ORDER BY table_name, ordinal_position
    """, (TABLES,))
    keys = database.fetch("""
        SELECT tc.table_name, kcu.column_name, tc.constraint_type,
               ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name AND kcu.table_name = tc.table_name
        LEFT JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name AND tc.constraint_type = 'FOREIGN KEY'
        WHERE tc.table_schema = 'public' AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
    """)
    primary = set()
    foreign = set()
    edges = set()
    for row in keys.to_dict("records"):
        if row["constraint_type"] == "PRIMARY KEY":
            primary.add((row["table_name"], row["column_name"]))
        else:
            foreign.add((row["table_name"], row["column_name"]))
            edges.add((row["foreign_table"], row["table_name"]))

    lines = ['digraph {', 'graph [rankdir=LR, bgcolor="transparent", nodesep="0.35", ranksep="0.8"];',
             'node [shape=plaintext, fontname="Helvetica", fontsize=10];',
             'edge [color="#8A7B6D", arrowhead=crow, arrowtail=tee, dir=both, penwidth=1.2];']
    for table in TABLES:
        header_color = "#1E1B18"
        if table in ["menu_price_history", "order_status_history"]:
            header_color = "#2A9D8F"
        rows = '<tr><td bgcolor="' + header_color + '" align="left"><font color="#FBF7F2"><b>' + table.upper() + "</b></font></td></tr>"
        for column in columns[columns["table_name"] == table].to_dict("records"):
            mark = ""
            if (table, column["column_name"]) in primary:
                mark = "PK "
            if (table, column["column_name"]) in foreign:
                mark = mark + "FK "
            text = mark + column["column_name"] + "  <font color='#8A7B6D'>" + column["data_type"].replace("character varying", "varchar").replace("timestamp without time zone", "timestamp") + "</font>"
            if mark.startswith("PK"):
                text = "<b>" + text + "</b>"
            rows = rows + '<tr><td align="left" bgcolor="#FFFFFF">' + text + "</td></tr>"
        lines.append(table + ' [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4" color="#E6D9C9">' + rows + "</table>>];")
    for parent, child in sorted(edges):
        lines.append(parent + " -> " + child + ";")
    lines.append("}")
    return "\n".join(lines)


def constraint_list():
    return database.fetch("""
        SELECT conrelid::regclass::text AS table_name,
               conname AS constraint_name,
               CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY' WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK' END AS type,
               pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace AND contype IN ('p', 'f', 'u', 'c')
        ORDER BY table_name, type
    """)


def show():
    style.hero("Rubric 1 + 2 · Dataset & database design",
               "From a real-world problem to a normalized schema",
               "Food delivery platforms juggle structured money data, fast-changing locations and a stream of status events. "
               "This page explains the dataset and shows the live schema straight from PostgreSQL's catalog.")

    style.section("01", "Problem statement")
    left, right = st.columns([3, 2])
    left.markdown(
        "Food delivery platforms generate large volumes of **structured** data (customers, restaurants, orders, payments), "
        "**semi-structured** data (order tracking events whose shape varies per order) and **location** data (restaurants, "
        "customers and riders moving across the city). A single conventional relational database is not the best fit for every one of these.\n\n"
        "FoodFlow uses a **hybrid architecture**: PostgreSQL guarantees correctness for money and inventory using transactions and constraints, "
        "spatial queries answer *who can deliver to me*, temporal tables answer *what did this cost last month*, and MongoDB stores the event stream."
    )
    with right:
        style.card("Why database technology is needed",
                   "Thousands of customers ordering at lunch peak need concurrency control so the last biryani is not sold twice, "
                   "payments must be atomic, data must survive crashes, and different staff must only see what they are allowed to.")
        style.card("Scale of the problem", "Mumbai alone has thousands of outlets. Our dataset models 120 restaurants, 1,500 customers and 15,000 orders over 6 months.")

    style.section("02", "Dataset", "Synthetic dataset generated for academic experimentation based on real-world food delivery workflows.")
    counts = []
    total = 0
    for table in TABLES:
        count = database.fetch_value("SELECT COUNT(*) FROM " + table)
        counts.append({"table": table, "rows": count, "what it stores": TABLE_NOTES[table]})
        total = total + count
    counts_frame = pd.DataFrame(counts)
    style.kpis([("Total records", style.number(total), "across 11 tables"),
                ("Localities", "25", "real Mumbai neighbourhoods"),
                ("Time span", "180 days", "with weekday and meal-time peaks"),
                ("Cuisines", "12", "with realistic menus and prices")])
    st.write("")
    left, right = st.columns([2, 3])
    with left:
        st.markdown("**How the data was created**")
        st.markdown(
            "- 25 real Mumbai localities with true GPS centres; points are scattered around them\n"
            "- Customers order from nearby restaurants (distance-weighted choice)\n"
            "- Order times follow lunch and dinner peaks, weekends are 35% busier, volume grows over time\n"
            "- Prep and travel time depend on cuisine, distance and rush hour\n"
            "- 3% payment failures, 2% restaurant cancellations, refunds for prepaid orders\n"
            "- 35% of dishes had price changes, and each order uses the price valid at that moment\n"
            "- Fixed random seed, so the dataset is reproducible (`core/generator.py`)"
        )
    with right:
        figure = px.bar(counts_frame.sort_values("rows"), x="rows", y="table", orientation="h", text="rows", title="Rows per table")
        figure.update_traces(marker_color=style.ORANGE, texttemplate="%{text:,}")
        figure.update_layout(height=380, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(figure, width="stretch")
    st.dataframe(counts_frame, hide_index=True, width="stretch")

    st.markdown("**Sample rows**")
    tabs = st.tabs(TABLES)
    for i in range(len(TABLES)):
        with tabs[i]:
            sample = database.fetch("SELECT * FROM " + TABLES[i] + " ORDER BY 1 LIMIT 8")
            if "geom" in sample.columns:
                sample = sample.drop(columns=["geom"])
            st.dataframe(sample, hide_index=True, width="stretch")
            file_name = {"customer": "customers", "restaurant": "restaurants", "menu_item": "menu_items", "delivery_partner": "delivery_partners",
                         "order_item": "order_items", "payment": "payments", "delivery": "deliveries", "review": "reviews"}.get(TABLES[i], TABLES[i])
            path = os.path.join(config.DATA_FOLDER, file_name + ".csv")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    st.download_button("Download " + file_name + ".csv", f.read(), file_name=file_name + ".csv", key="dl" + TABLES[i])

    style.section("03", "Entity relationship diagram", "Generated live from PostgreSQL's information_schema. Crow's feet mark the 'many' side. Green tables hold temporal history.")
    st.graphviz_chart(er_diagram(), width="stretch")

    style.section("04", "Keys and constraints", "Every rule below is enforced by the database itself, not by the app.")
    constraints = constraint_list()
    summary = constraints.groupby("type").size().reset_index(name="count")
    columns = st.columns(len(summary))
    for i in range(len(summary)):
        columns[i].metric(summary.iloc[i]["type"], int(summary.iloc[i]["count"]))
    chosen = st.multiselect("Filter by type", ["PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK"], default=["CHECK", "FOREIGN KEY"])
    st.dataframe(constraints[constraints["type"].isin(chosen)], hide_index=True, width="stretch", height=320)

    with st.expander("Try to break a constraint"):
        attempts = {
            "Negative order total": "INSERT INTO orders (customer_id, restaurant_id, order_time, status, total_amount) VALUES (1, 1, NOW(), 'PLACED', -50);",
            "Unknown order status": "UPDATE orders SET status = 'TELEPORTED' WHERE order_id = 100001;",
            "Order for a customer that does not exist": "INSERT INTO orders (customer_id, restaurant_id, order_time, status, total_amount) VALUES (999999, 1, NOW(), 'PLACED', 100);",
            "Duplicate customer email": "INSERT INTO customer VALUES (99999, 'Test', '9000000000', (SELECT email FROM customer LIMIT 1), 'x', 'Powai', 19.1, 72.9, CURRENT_DATE);",
            "Stock below zero": "UPDATE menu_item SET stock = -1 WHERE item_id = 1001;",
            "Review with 7 stars": "UPDATE review SET stars = 7 WHERE review_id = 1;",
        }
        pick = st.selectbox("Pick a bad statement", list(attempts.keys()))
        st.code(attempts[pick], language="sql")
        if st.button("Run it"):
            connection = database.connect(autocommit=False)
            try:
                connection.cursor().execute(attempts[pick])
                st.warning("The statement went through (rolled back anyway).")
            except Exception as error:
                st.error("Rejected by PostgreSQL: " + str(error).splitlines()[0])
            finally:
                connection.rollback()
                connection.close()

    style.section("05", "Normalization")
    columns = st.columns(4)
    for i in range(4):
        with columns[i]:
            style.card(NORMAL_FORMS[i][0], NORMAL_FORMS[i][1])

    style.section("06", "Triggers and stored functions")
    triggers = database.fetch("""
        SELECT event_object_table AS table_name, trigger_name, action_timing || ' ' || event_manipulation AS fires_on, action_statement
        FROM information_schema.triggers ORDER BY event_object_table
    """)
    st.dataframe(triggers, hide_index=True, width="stretch")
    style.footer()
