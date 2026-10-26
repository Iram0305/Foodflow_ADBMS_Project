import pandas as pd
import streamlit as st

from core import hood
from core import nav
from core import shop
from core import style


def reorder(order_id):
    restaurant_id, items = shop.reorder(order_id)
    if restaurant_id is None or not items:
        st.toast("Sorry, those items are not available right now.")
        return
    st.session_state["cart"] = {"restaurant_id": restaurant_id, "items": items}
    st.session_state["restaurant_id"] = restaurant_id
    nav.go("menu")


def show():
    customer = st.session_state["customer"]
    head, button = st.columns([14, 1.4])
    head.markdown("## Your orders")
    with button:
        st.write("")
        want_sql = st.button("</> SQL", key="hoodorders", help="See the database work behind this page")
    frame, sql_text = shop.my_orders(customer["customer_id"])
    if len(frame) == 0:
        st.info("You have not ordered yet. Hungry?")
        if st.button("Browse restaurants", type="primary"):
            nav.go("discover")
    else:
        delivered = frame[frame["status"] == "DELIVERED"]
        style.kpis([("Orders", style.number(len(frame)), "recent"), ("Spent", shop.rupees(delivered["total_amount"].astype(float).sum()), "on delivered orders"),
                    ("Favourite", frame["restaurant"].mode().iloc[0], "most ordered")])
        for row in frame.to_dict("records"):
            status = row["status"]
            chip = "sf-chip-live"
            if status in ["DELIVERED", "CANCELLED"]:
                chip = "sf-chip-" + status
            with st.container(border=True):
                info, actions = st.columns([4, 1.6])
                with info:
                    st.markdown('<div class="sf-order-title">' + style.safe(row["restaurant"]) + '</div><span class="sf-chip ' + chip + '">' + status.replace("_", " ").title() + "</span> "
                                "<span style='color:#7A6F65'>" + shop.clock_text(row["order_time"]) + " · " + shop.rupees(row["total_amount"]) + "</span>", unsafe_allow_html=True)
                    st.caption(row["items"] or "")
                    if row["stars"] is not None and not pd.isna(row["stars"]):
                        st.caption("Your rating: " + "★" * int(row["stars"]))
                with actions:
                    if status not in ["DELIVERED", "CANCELLED"]:
                        if st.button("Track", key="t" + str(row["order_id"]), type="primary", width="stretch"):
                            st.session_state["track_order_id"] = int(row["order_id"])
                            nav.go("track")
                    else:
                        if st.button("Order again", key="r" + str(row["order_id"]), width="stretch"):
                            reorder(int(row["order_id"]))
                        if status == "DELIVERED" and st.button("Details", key="d" + str(row["order_id"]), width="stretch"):
                            st.session_state["track_order_id"] = int(row["order_id"])
                            nav.go("track")
    if want_sql:
        hood.my_orders(sql_text, customer["customer_id"])
    style.footer()
