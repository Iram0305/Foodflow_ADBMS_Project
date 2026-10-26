import json

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

from core import database
from core import orders
from core import style
from core import tracking


def to_text(doc):
    return json.dumps(doc, indent=2, default=str)


def show():
    collection, mode, error = tracking.get_store()
    style.hero("Rubric 3C · NoSQL with MongoDB",
               "Order tracking as a living document",
               "Tracking events are semi-structured and arrive constantly. Each order is one MongoDB document with a growing array of events, "
               "GeoJSON points and a route line. Cancelled orders carry a reason, delivered ones carry a partner. No schema migration needed.",
               ["Document model", "Embedded arrays", "GeoJSON", "$push updates", "Aggregation pipeline", "Polyglot persistence"])
    if mode != "MongoDB":
        style.banner("warn", "🧪", "Running on " + mode,
                     "No MongoDB server was reachable, so an in-memory MongoDB-compatible engine is used. Set MONGO_URI to a real server or MongoDB Atlas for the full setup.")

    stats = tracking.document_stats()
    style.kpis([("Documents", style.number(stats["documents"]), "one per order"),
                ("With GeoJSON route", style.number(stats["with_route"]), "delivery path"),
                ("Live orders", style.number(stats["live"]), "not yet delivered"),
                ("Engine", "MongoDB" if mode == "MongoDB" else "mongomock", "collection: order_tracking")])

    style.section("01", "Track an order")
    live = tracking.active_orders(40)
    recent = tracking.recent_orders(20)
    options = {}
    for doc in live + recent:
        label = "#" + str(doc["order_id"]) + " · " + doc["current_status"] + " · " + doc["restaurant"]["name"] + " → " + doc["customer"]["name"]
        options[label] = doc["order_id"]
    manual = st.text_input("Or type any order id", "")
    pick = st.selectbox("Pick a live or recent order", list(options.keys()))
    order_id = options[pick]
    if manual.strip().isdigit():
        order_id = int(manual.strip())

    doc = tracking.get_document(order_id)
    if doc is None:
        st.warning("No tracking document for that order.")
        style.footer()
        return

    reached = []
    times = {}
    for event in doc["events"]:
        reached.append(event["status"])
        times[event["status"]] = pd.Timestamp(event["time"]).strftime("%d %b %H:%M")
    if doc["current_status"] == "CANCELLED":
        style.banner("bad", "✖️", "Order #" + str(order_id) + " was cancelled", str(doc["events"][-1].get("reason", "")))
    style.tracker(tracking.STATUS_FLOW, reached, times)

    action_left, action_right, spacer = st.columns([1, 1, 3])
    if action_left.button("Advance to next status", type="primary", disabled=doc["current_status"] in ["DELIVERED", "CANCELLED"]):
        new_status, log = orders.advance_order(order_id)
        st.session_state["advance_log"] = (order_id, new_status, log)
        st.rerun()
    if action_right.button("Cancel order", disabled=doc["current_status"] in ["DELIVERED", "CANCELLED", "PICKED_UP"]):
        done, message = orders.cancel_order(order_id)
        st.session_state["advance_log"] = (order_id, "CANCELLED" if done else None, [message])
        st.rerun()
    if "advance_log" in st.session_state and st.session_state["advance_log"][0] == order_id:
        for line in st.session_state["advance_log"][2]:
            st.caption("• " + line)

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**The MongoDB document**")
        st.code(to_text(doc), language="json")
    with right:
        st.markdown("**Same order in PostgreSQL**")
        history = database.fetch("SELECT status, changed_at FROM order_status_history WHERE order_id = %s ORDER BY changed_at, history_id", (int(order_id),))
        st.dataframe(history, hide_index=True, width="stretch")
        st.caption("PostgreSQL needs a separate history table and joins. MongoDB embeds the events inside the order itself.")
        if "route" in doc:
            path = [{"path": doc["route"]["coordinates"]}]
            start = doc["route"]["coordinates"][0]
            end = doc["route"]["coordinates"][-1]
            points = pd.DataFrame([{"lon": start[0], "lat": start[1], "kind": "Restaurant", "color": [232, 83, 43]},
                                   {"lon": end[0], "lat": end[1], "kind": "Customer", "color": [30, 27, 24]}])
            deck = pdk.Deck(
                map_style="light",
                initial_view_state=pdk.ViewState(latitude=(start[1] + end[1]) / 2, longitude=(start[0] + end[0]) / 2, zoom=13),
                layers=[pdk.Layer("PathLayer", path, get_path="path", get_color=[232, 83, 43], width_min_pixels=4),
                        pdk.Layer("ScatterplotLayer", points, get_position=["lon", "lat"], get_fill_color="color", get_radius=90, pickable=True)],
                tooltip={"text": "{kind}"})
            st.pydeck_chart(deck, height=260)

    style.section("02", "Aggregation pipelines", "Analytics computed inside MongoDB over all tracking documents.")
    name = st.selectbox("Pipeline", list(tracking.PIPELINES.keys()))
    left, right = st.columns([2, 3])
    with left:
        st.code(json.dumps(tracking.PIPELINES[name], indent=2), language="json")
    with right:
        result = pd.DataFrame(tracking.run_pipeline(name))
        if "_id" in result.columns:
            result = result.rename(columns={"_id": "group"})
        for column in result.columns:
            if result[column].dtype == float:
                result[column] = result[column].round(2)
        st.dataframe(result, hide_index=True, width="stretch")
        if name == "Average minutes spent in each stage" and len(result) > 0:
            melted = result.melt(id_vars=["group"], value_vars=["to_accept", "to_start_cooking", "cooking", "on_the_road"], var_name="stage", value_name="minutes")
            figure = px.bar(melted, x="minutes", y="group", color="stage", orientation="h", title="Where the time goes, by cuisine")
            figure.update_layout(height=420, yaxis_title=None, legend_title=None)
            st.plotly_chart(figure, width="stretch")
        elif name == "Tracking events by hour of day":
            figure = px.bar(result, x="group", y="events", title="Events per hour")
            figure.update_traces(marker_color=style.ORANGE)
            st.plotly_chart(figure, width="stretch")

    style.section("03", "Why two databases?")
    columns = st.columns(3)
    with columns[0]:
        style.card("PostgreSQL for money", "Orders, payments and stock need constraints, joins and ACID transactions. A wrong rupee is not acceptable.")
    with columns[1]:
        style.card("MongoDB for events", "Every order has a different number of events, optional fields (reason, partner, route) and is written constantly. A document fits naturally.")
    with columns[2]:
        style.card("How they stay in sync", "PostgreSQL commits first. Right after COMMIT the app rebuilds that order's document in MongoDB, so Postgres stays the source of truth.")
    style.footer()
