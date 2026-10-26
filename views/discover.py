import streamlit as st

from core import hood
from core import nav
from core import shop
from core import shopstyle
from core import style

SORTS = {
    "Nearest first": ("distance_km", True),
    "Top rated": ("rating", False),
    "Fastest delivery": ("eta_minutes", True),
    "Cost: low to high": ("cost_for_two", True),
    "Most popular": ("total_orders", False),
}


def open_menu(restaurant_id):
    cart = st.session_state["cart"]
    if cart["items"] and cart["restaurant_id"] != restaurant_id:
        cart["items"] = {}
        st.toast("Your cart was cleared. You can order from one restaurant at a time.")
    cart["restaurant_id"] = restaurant_id
    st.session_state["restaurant_id"] = restaurant_id
    nav.go("menu")


def more_cards():
    st.session_state["show_limit"] = st.session_state.get("show_limit", 12) + 12


def reset_limit():
    st.session_state["show_limit"] = 12


def show():
    customer = st.session_state["customer"]
    first_name = customer["name"].split(" ")[0]
    head, button = st.columns([14, 1.4])
    with button:
        st.write("")
        want_sql = st.button("</> SQL", key="hooddiscover", help="See the database work behind this page")

    st.markdown('<div class="sf-banner"><div class="sf-float">🍜🍕</div><h1>Hi ' + style.safe(first_name) + ", what are you craving?</h1>"
                "<p>Delivering to " + style.safe(customer["address"]) + "</p>"
                '<span class="sf-pill">Free delivery above ₹199</span><span class="sf-pill">Live rider tracking</span><span class="sf-pill">Pay by UPI, card or cash</span></div>',
                unsafe_allow_html=True)

    active = shop.active_order(customer["customer_id"])
    if active is not None:
        box, action = st.columns([5, 1.5])
        box.info("🛵 Your order #" + str(active["order_id"]) + " from " + active["restaurant"] + " is " + active["status"].replace("_", " ").lower() + ".")
        if action.button("Track order", type="primary", width="stretch", key="banner_track"):
            st.session_state["track_order_id"] = int(active["order_id"])
            nav.go("track")

    frame, sql_text, elapsed = shop.restaurants_near(customer["latitude"], customer["longitude"], 8)
    cuisines = sorted(frame["cuisine"].unique().tolist())

    top = st.columns([3, 2, 2, 1.4])
    search = top[0].text_input("Search", placeholder="Search restaurants or cuisines", label_visibility="collapsed", on_change=reset_limit, key="search_box")
    sort_name = top[1].selectbox("Sort by", list(SORTS.keys()), label_visibility="collapsed", key="sort_box")
    cuisine_pick = top[2].selectbox("Cuisine", ["All cuisines"] + cuisines, label_visibility="collapsed", on_change=reset_limit, key="cuisine_box")
    veg_only = top[3].toggle("Pure veg", key="veg_box", on_change=reset_limit)

    shown = frame.copy()
    if search.strip():
        text = search.strip().lower()
        shown = shown[shown["name"].str.lower().str.contains(text) | shown["cuisine"].str.lower().str.contains(text) | shown["locality"].str.lower().str.contains(text)]
    if cuisine_pick != "All cuisines":
        shown = shown[shown["cuisine"] == cuisine_pick]
    if veg_only:
        shown = shown[shown["is_veg"]]
    column, ascending = SORTS[sort_name]
    shown = shown.sort_values(column, ascending=ascending)

    popular_cutoff = frame["total_orders"].quantile(0.85)
    st.markdown("**" + str(len(shown)) + " restaurants** deliver to you")

    if len(shown) == 0:
        st.info("No restaurants match. Try clearing the filters.")

    limit = st.session_state.get("show_limit", 12)
    rows = shown.head(limit).to_dict("records")
    for start in range(0, len(rows), 3):
        columns = st.columns(3)
        for offset in range(3):
            if start + offset >= len(rows):
                break
            row = rows[start + offset]
            badge = ""
            if row["total_orders"] >= popular_cutoff:
                badge = "Popular"
            with columns[offset]:
                with st.container(border=True):
                    st.markdown(shopstyle.restaurant_card_html(row, badge), unsafe_allow_html=True)
                    if st.button("View menu", key="open" + str(row["restaurant_id"]), width="stretch"):
                        open_menu(int(row["restaurant_id"]))
    if len(shown) > limit:
        st.button("Show more restaurants", on_click=more_cards, width="stretch")

    if want_sql:
        hood.discover(sql_text, len(frame), elapsed, customer["latitude"], customer["longitude"])
    style.footer()
