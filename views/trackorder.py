import pandas as pd
import pydeck as pdk
import streamlit as st

from core import hood
from core import nav
from core import orders
from core import shop
from core import style
from core import tracking

FINISHED = ["DELIVERED", "CANCELLED"]


def history_times(order_id):
    times = {}
    history = shop.order_history(order_id)
    for row in history.to_dict("records"):
        times[row["status"]] = shop.local_time(row["changed_at"]).strftime("%I:%M %p").lstrip("0")
    return times


def zoom_for(info):
    span = max(abs(info["r_lat"] - info["c_lat"]), abs(info["r_lon"] - info["c_lon"]))
    if span < 0.004:
        return 15
    if span < 0.01:
        return 14
    if span < 0.02:
        return 13
    return 12


def map_view(info, speed):
    route = shop.route_points(info)
    rider_lon, rider_lat = shop.rider_position(info, route, speed)
    path = pd.DataFrame([{"path": route}])
    places = pd.DataFrame([
        {"name": info["restaurant"], "lon": info["r_lon"], "lat": info["r_lat"], "color": [232, 93, 4, 255]},
        {"name": "You", "lon": info["c_lon"], "lat": info["c_lat"], "color": [42, 157, 143, 255]},
    ])
    layers = [
        pdk.Layer("PathLayer", path, get_path="path", get_color=[30, 27, 24, 200], width_min_pixels=4),
        pdk.Layer("ScatterplotLayer", places, get_position=["lon", "lat"], get_fill_color="color", get_radius=90, radius_min_pixels=9),
    ]
    if info["status"] in ["PICKED_UP", "DELIVERED"]:
        rider = pd.DataFrame([{"lon": rider_lon, "lat": rider_lat}])
        layers.append(pdk.Layer("ScatterplotLayer", rider, get_position=["lon", "lat"], get_fill_color=[242, 165, 65, 255],
                                get_line_color=[30, 27, 24, 255], stroked=True, line_width_min_pixels=3, get_radius=110, radius_min_pixels=13))
    centre_lat = (info["r_lat"] + info["c_lat"]) / 2
    centre_lon = (info["r_lon"] + info["c_lon"]) / 2
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=centre_lat, longitude=centre_lon, zoom=zoom_for(info)),
                             map_style="light", tooltip={"text": "{name}"}), height=360)


def rider_card(info):
    if info["partner_name"] is None or info["status"] in ["PLACED", "ACCEPTED"]:
        st.markdown("🛵 A delivery partner will be assigned as soon as your food is being prepared.")
        return
    st.markdown('<div class="sf-rider"><div class="sf-avatar">🧑‍🦱</div><div><b>' + style.safe(info["partner_name"]) + "</b><br>"
                "<span style='color:#7A6F65'>" + style.safe(info["vehicle"]) + " · ⭐ " + str(info["partner_rating"]) + "</span></div></div><div style='height:6px'></div>", unsafe_allow_html=True)


def rating_box(info):
    existing = shop.my_orders(info["customer_id"])[0]
    row = existing[existing["order_id"] == info["order_id"]]
    if len(row) > 0 and row.iloc[0]["stars"] is not None and not pd.isna(row.iloc[0]["stars"]):
        st.success("You rated this order " + str(int(row.iloc[0]["stars"])) + " out of 5. Thank you!")
        return
    st.markdown("**How was your food?**")
    stars = st.feedback("stars", key="stars" + str(info["order_id"]))
    comment = st.text_input("Tell us more (optional)", key="comment" + str(info["order_id"]))
    if st.button("Submit rating", disabled=stars is None, key="rate" + str(info["order_id"])):
        ok, message, sql = shop.add_review(info["order_id"], info["customer_id"], info["restaurant_id"], stars + 1, comment)
        if ok:
            st.toast(message)
            st.rerun()
        else:
            st.error(message)


def render(order_id):
    speed = shop.SPEEDS[st.session_state.get("speed") or "Demo (about 2 min)"]
    shop.progress_order(order_id, speed)
    info = shop.track_info(order_id)
    status = info["status"]
    tracking.refresh_order(order_id)

    if status == "DELIVERED" and st.session_state.get("celebrated") != order_id:
        st.session_state["celebrated"] = order_id
        st.balloons()

    sub = "From " + info["restaurant"]
    if status == "PICKED_UP":
        sub = "Your rider is heading to " + info["customer_address"].split(",")[0]
    st.markdown('<div class="sf-status"><div class="sf-status-icon">' + shop.STATUS_ICON[status] + '</div><div><div class="sf-status-title">' + shop.STATUS_TITLE[status] +
                '</div><div class="sf-status-sub">' + style.safe(sub) + '</div></div><div class="sf-eta"><div class="sf-eta-label">Arriving in</div><div class="sf-eta-value">' +
                shop.eta_text(info, speed) + "</div></div></div>", unsafe_allow_html=True)

    if status != "CANCELLED":
        reached = tracking.STATUS_FLOW[:tracking.STATUS_FLOW.index(status) + 1]
        style.tracker(tracking.STATUS_FLOW, reached, history_times(order_id))

    left, right = st.columns([3, 2], gap="large")
    with left:
        map_view(info, speed)
    with right:
        with st.container(border=True):
            st.markdown("**Delivery partner**")
            rider_card(info)
        with st.container(border=True):
            st.markdown("**Order #" + str(order_id) + "**")
            lines = shop.order_lines(order_id)
            for line in lines.to_dict("records"):
                st.markdown(str(line["quantity"]) + " × " + style.safe(line["item_name"]) + " · " + shop.rupees(line["line_total"]))
            payment = {"SUCCESS": "Paid", "PAID": "Paid", "PENDING": "Pay on delivery", "FAILED": "Not charged", "REFUNDED": "Refunded"}.get(info["payment_status"], info["payment_status"])
            st.caption("Total " + shop.rupees(info["total_amount"]) + " · " + str(info["method"]).title() + " · " + payment)
        if status in ["PLACED", "ACCEPTED", "PREPARING"]:
            if st.button("Cancel order", key="cancel" + str(order_id), width="stretch"):
                ok, message = orders.cancel_order(order_id)
                if ok:
                    tracking.refresh_order(order_id)
                    st.toast("Order cancelled. Any payment will be refunded.")
                else:
                    st.error(message)
                st.rerun()
    if status == "DELIVERED":
        rating_box(info)
    if status in FINISHED and st.session_state.get("track_done") != (order_id, status):
        st.session_state["track_done"] = (order_id, status)
        st.rerun()


def show():
    order_id = st.session_state.get("track_order_id")
    customer = st.session_state["customer"]
    head, button = st.columns([14, 1.4])
    head.markdown("## Track your order")
    if order_id is None:
        st.info("You have no order to track yet.")
        if st.button("Browse restaurants", type="primary"):
            nav.go("discover")
        return
    info = shop.track_info(order_id)
    if info is None or info["customer_id"] != customer["customer_id"]:
        st.warning("We could not find that order.")
        return
    with button:
        st.write("")
        want_sql = st.button("</> SQL", key="hoodtrack", help="See the database work behind this page")
    pick, speed_box = st.columns([3, 3])
    pick.caption("Order #" + str(order_id) + " · placed " + shop.clock_text(info["order_time"]))
    with speed_box:
        st.segmented_control("Demo speed", list(shop.SPEEDS.keys()), key="speed", label_visibility="collapsed")

    refresh = None
    if info["status"] not in FINISHED:
        refresh = 3
    fragment = st.fragment(render, run_every=refresh)
    fragment(order_id)
    if want_sql:
        hood.tracking_view(order_id, shop.track_info(order_id))
    style.footer()
