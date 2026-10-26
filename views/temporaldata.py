from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import database
from core import style
from core import temporal

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def show():
    style.hero("Rubric 3 · Temporal data",
               "Every price has a lifetime",
               "menu_price_history is a valid-time table: each row says from when until when a price was true. A trigger maintains it automatically, "
               "so we can ask what the menu looked like on any past date, and every order keeps the price that was valid when it was placed.",
               ["Valid time", "Transaction time", "Temporal trigger", "Time-travel query", "LAG / LEAD", "Interval arithmetic"])

    restaurants = database.fetch("SELECT restaurant_id, name, locality FROM restaurant ORDER BY name")
    labels = {}
    for row in restaurants.to_dict("records"):
        labels[row["name"] + " · " + row["locality"]] = int(row["restaurant_id"])

    style.section("01", "Price history of a dish")
    changed = database.fetch("""
        SELECT m.item_id, m.item_name, r.name AS restaurant, COUNT(*) AS versions
        FROM menu_price_history h JOIN menu_item m ON m.item_id = h.item_id JOIN restaurant r ON r.restaurant_id = m.restaurant_id
        GROUP BY m.item_id, m.item_name, r.name ORDER BY versions DESC, m.item_name LIMIT 80
    """)
    item_labels = {}
    for row in changed.to_dict("records"):
        item_labels[row["item_name"] + " · " + row["restaurant"] + " (" + str(row["versions"]) + " versions)"] = int(row["item_id"])
    pick = st.selectbox("Dish", list(item_labels.keys()))
    item_id = item_labels[pick]
    history, elapsed = temporal.price_history(item_id)

    left, right = st.columns([3, 2])
    with left:
        now = database.fetch_value("SELECT NOW()::timestamp")
        figure = go.Figure()
        for row in history.to_dict("records"):
            end = row["valid_to"]
            if end is None or pd.isna(end):
                end = now
            figure.add_trace(go.Scatter(x=[row["valid_from"], end], y=[row["price"], row["price"]], mode="lines+markers",
                                        line=dict(width=6, color=style.ORANGE if row["state"] == "current" else style.INK), showlegend=False,
                                        hovertemplate="Rs %{y}<extra></extra>"))
        figure.update_layout(title="Price over time (each segment is one validity period)", height=300, yaxis_title="Rs")
        st.plotly_chart(figure, width="stretch")
    with right:
        st.code(temporal.PRICE_HISTORY_SQL.strip(), language="sql")
        st.dataframe(history, hide_index=True, width="stretch")

    with st.expander("Change this price now and watch the trigger"):
        current_price = float(database.fetch_value("SELECT price FROM menu_item WHERE item_id = %s", (item_id,)))
        new_price = st.number_input("New price (Rs)", min_value=5.0, max_value=5000.0, value=current_price + 10, step=5.0)
        st.code("UPDATE menu_item SET price = " + str(new_price) + " WHERE item_id = " + str(item_id) + ";", language="sql")
        if st.button("Update price"):
            ok, message = temporal.change_price(item_id, new_price)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    style.section("02", "Time travel: the menu on any past date")
    left, right = st.columns([2, 1])
    restaurant_pick = left.selectbox("Restaurant", list(labels.keys()), index=5)
    days_back = right.slider("Days ago", 0, 200, 90)
    moment = database.fetch_value("SELECT NOW()::timestamp") - timedelta(days=days_back)
    as_of, as_of_ms = temporal.menu_as_of(labels[restaurant_pick], moment)
    st.caption("Showing prices that were valid on " + moment.strftime("%d %b %Y, %H:%M"))
    left, right = st.columns([3, 2])
    with left:
        if len(as_of) == 0:
            st.info("This restaurant had no menu that far back.")
        else:
            st.dataframe(as_of, hide_index=True, width="stretch",
                         column_config={"change_percent": st.column_config.NumberColumn("Change since then", format="%.1f %%")})
    with right:
        st.code(temporal.MENU_AS_OF_SQL.strip(), language="sql")

    style.section("03", "Recent price changes", "LAG() pairs every new price with the one it replaced.")
    changes = temporal.recent_changes()
    changes["change"] = changes["new_price"] - changes["old_price"]
    st.dataframe(changes.head(25), hide_index=True, width="stretch")

    style.section("04", "Order lifecycle durations", "order_status_history is transaction-time data: when each change was recorded. LEAD() turns it into time spent in each state.")
    recent = database.fetch("SELECT order_id FROM orders WHERE status = 'DELIVERED' ORDER BY order_time DESC LIMIT 30")["order_id"].tolist()
    order_id = st.selectbox("Delivered order", recent)
    lifecycle, lifecycle_ms = temporal.order_lifecycle(order_id)
    left, right = st.columns([3, 2])
    with left:
        chart = lifecycle.dropna(subset=["next_change"])
        if len(chart) > 0:
            figure = px.timeline(chart, x_start="changed_at", x_end="next_change", y="status", color="status", title="Order #" + str(order_id))
            figure.update_yaxes(autorange="reversed")
            figure.update_layout(height=280, showlegend=False, yaxis_title=None)
            st.plotly_chart(figure, width="stretch")
        st.dataframe(lifecycle, hide_index=True, width="stretch")
    with right:
        st.code(temporal.ORDER_LIFECYCLE_SQL.strip(), language="sql")

    style.section("05", "Temporal patterns")
    heat = temporal.weekly_heatmap()
    grid = heat.pivot(index="weekday", columns="hour", values="orders").fillna(0)
    grid.index = [DAYS[i - 1] for i in grid.index]
    figure = px.imshow(grid, aspect="auto", color_continuous_scale=["#FBF7F2", "#F2A541", "#E8532B", "#7A1A10"], title="Orders by weekday and hour")
    figure.update_layout(height=330, xaxis_title="Hour of day", yaxis_title=None, coloraxis_showscale=False)
    st.plotly_chart(figure, width="stretch")

    trend = temporal.delivery_trend()
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=trend["week"], y=trend["p90_minutes"], name="90th percentile", line=dict(color=style.INK, dash="dot")))
    figure.add_trace(go.Scatter(x=trend["week"], y=trend["avg_minutes"], name="Average", line=dict(color=style.ORANGE, width=3)))
    figure.update_layout(title="Weekly delivery time (minutes)", height=320, legend=dict(orientation="h", y=1.12))
    st.plotly_chart(figure, width="stretch")
    with st.expander("SQL"):
        st.code(temporal.DELIVERY_TREND_SQL.strip(), language="sql")

    style.section("06", "Snapshot: what was happening at a past moment?", "Reconstructs each order's status as it was at a chosen time, using DISTINCT ON over the history table.")
    left, right = st.columns([1, 2])
    hours_back = left.slider("Hours ago", 0, 72, 3)
    snapshot_time = database.fetch_value("SELECT NOW()::timestamp") - timedelta(hours=hours_back)
    snapshot, snapshot_ms = temporal.state_at(snapshot_time)
    with left:
        st.caption("At " + snapshot_time.strftime("%d %b %H:%M") + " (orders from the 3 hours before)")
        st.dataframe(snapshot, hide_index=True, width="stretch")
    with right:
        st.code(temporal.STATE_AT_SQL.strip(), language="sql")
    style.footer()
