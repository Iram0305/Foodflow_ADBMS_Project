import streamlit as st

from core import hood
from core import nav
from core import shop
from core import shopstyle
from core import style

MAX_PER_ITEM = 10


def change_quantity(item_id, change, stock):
    items = st.session_state["cart"]["items"]
    new_quantity = items.get(item_id, 0) + change
    new_quantity = max(0, min(new_quantity, stock, MAX_PER_ITEM))
    if new_quantity == 0:
        items.pop(item_id, None)
    else:
        items[item_id] = new_quantity


def clear_cart():
    st.session_state["cart"]["items"] = {}


def stepper(item_id, quantity, stock):
    if quantity == 0:
        st.button("ADD", key="add" + str(item_id), on_click=change_quantity, args=(item_id, 1, stock), width="stretch")
        return
    minus, number, plus = st.columns([1, 1, 1])
    minus.button("−", key="minus" + str(item_id), on_click=change_quantity, args=(item_id, -1, stock))
    number.markdown('<div class="sf-qty">' + str(quantity) + "</div>", unsafe_allow_html=True)
    plus.button("+", key="plus" + str(item_id), on_click=change_quantity, args=(item_id, 1, stock), disabled=quantity >= min(stock, MAX_PER_ITEM))


def cart_panel(menu_frame):
    st.markdown("### Your cart")
    items = st.session_state["cart"]["items"]
    if not items:
        st.markdown("🛒 Your cart is empty. Add something tasty from the menu.")
        return
    lines = []
    for row in menu_frame.to_dict("records"):
        if int(row["item_id"]) in items:
            row["quantity"] = items[int(row["item_id"])]
            lines.append(row)
    subtotal = 0
    for line in lines:
        subtotal = subtotal + float(line["price"]) * line["quantity"]
    st.markdown(shopstyle.bill_html(lines, shop.bill(subtotal)), unsafe_allow_html=True)
    st.write("")
    if st.button("Proceed to checkout", type="primary", width="stretch", key="to_checkout"):
        nav.go("checkout")
    st.button("Clear cart", on_click=clear_cart, width="stretch", key="clear_cart")


def show():
    customer = st.session_state["customer"]
    restaurant_id = st.session_state.get("restaurant_id")
    if restaurant_id is None:
        st.info("Pick a restaurant first.")
        if st.button("Browse restaurants", type="primary"):
            nav.go("discover")
        return

    restaurant = shop.restaurant_info(restaurant_id, customer["latitude"], customer["longitude"])
    menu_frame, sql_text, elapsed = shop.menu_for(restaurant_id)
    items = st.session_state["cart"]["items"]

    back, spacer, button = st.columns([2, 10, 1.6])
    if back.button("← All restaurants", key="back_discover"):
        nav.go("discover")
    with button:
        want_sql = st.button("</> SQL", key="hoodmenu", help="See the database work behind this page")

    emoji, light, strong = shopstyle.look(restaurant["cuisine"])
    veg_badge = ""
    if restaurant["is_veg"]:
        veg_badge = '<span class="sf-badge sf-badge-green">Pure veg</span>'
    st.markdown('<div class="sf-tile" style="height:120px;background: linear-gradient(135deg, ' + light + ", " + strong + ');"><span class="sf-tile-emoji" style="font-size:66px">' + emoji +
                '</span><span class="sf-tile-tag">' + style.safe(restaurant["cuisine"]) + "</span></div>"
                '<div class="sf-name" style="font-size:1.8rem">' + style.safe(restaurant["name"]) + "</div>"
                '<div class="sf-sub">' + style.safe(restaurant["address"]) + "</div>"
                '<div class="sf-meta">' + shopstyle.rating_badge(restaurant["rating"]) + "<span>" + str(restaurant["eta_minutes"]) + " mins</span><span>" +
                str(restaurant["distance_km"]) + " km away</span><span>" + shop.rupees(restaurant["cost_for_two"]) + " for two</span><span>Open " +
                restaurant["opens_at"] + " to " + restaurant["closes_at"] + "</span>" + veg_badge + "</div>", unsafe_allow_html=True)

    best = menu_frame[menu_frame["sold"] > 0].sort_values("sold", ascending=False).head(2)["item_id"].tolist()

    left, right = st.columns([3, 2], gap="large")
    with left:
        for category in menu_frame["category"].unique().tolist():
            st.markdown('<div class="sf-category">' + style.safe(category) + "</div>", unsafe_allow_html=True)
            for row in menu_frame[menu_frame["category"] == category].to_dict("records"):
                item_id = int(row["item_id"])
                stock = int(row["stock"])
                info, control = st.columns([4, 1.7])
                tags = ""
                if item_id in best:
                    tags = ' <span class="sf-badge">Bestseller</span>'
                stock_text = ""
                if stock == 0:
                    stock_text = '<div class="sf-soldout">Sold out</div>'
                elif stock <= 5:
                    stock_text = '<div class="sf-low">Only ' + str(stock) + " left</div>"
                with info:
                    st.markdown('<div class="sf-item"><div class="sf-item-name">' + shopstyle.veg_dot(row["is_veg"]) + style.safe(row["item_name"]) + tags +
                                '</div><div class="sf-item-price">' + shop.rupees(row["price"]) + "</div>" + stock_text + "</div>", unsafe_allow_html=True)
                with control:
                    st.write("")
                    if stock == 0:
                        st.button("Unavailable", key="soldout" + str(item_id), disabled=True, width="stretch")
                    else:
                        stepper(item_id, items.get(item_id, 0), stock)
    with right:
        with st.container(border=True):
            cart_panel(menu_frame)

    if want_sql:
        hood.menu(sql_text, len(menu_frame), elapsed, restaurant_id)
    style.footer()
