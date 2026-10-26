import os

import streamlit as st

st.set_page_config(page_title="FoodFlow · Food delivery", page_icon="🍲", layout="wide", initial_sidebar_state="collapsed")

from core import database
from core import loader
from core import nav
from core import shopstyle
from core import style
from core import tracking
from views import account, checkout, discover, login, menu, myorders, trackorder
from views import home, design, ordering, concurrencylab, livetracking, maps, temporaldata, querylab, dbaconsole

style.apply_theme()
shopstyle.apply()


def setup_screen(error_text):
    style.hero("Setup needed", "FoodFlow can't reach PostgreSQL yet",
               "Start the databases with Docker or point DATABASE_URL to your own PostgreSQL server, then refresh this page.")
    st.code(error_text, language="text")
    st.code("DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/foodflow\nMONGO_URI=mongodb://localhost:27017", language="bash")
    st.stop()


def build_screen():
    style.hero("First run", "Let's build the FoodFlow database",
               "This creates 11 tables, loads about 1.6 lakh rows of the Mumbai food delivery dataset, adds triggers, indexes, roles and row level security, then syncs tracking documents into MongoDB.",
               ["~30 seconds", "Runs once", "Safe to re-run"])
    if st.button("Build the database now", type="primary"):
        box = st.status("Building FoodFlow...", expanded=True)
        loader.build_database(progress=box.write)
        box.update(label="Database ready", state="complete")
        st.rerun()
    st.stop()


def sign_out():
    for key in ["customer", "cart", "restaurant_id", "track_order_id", "last_result", "celebrated", "track_done"]:
        st.session_state.pop(key, None)


def sidebar():
    customer = st.session_state["customer"]
    with st.sidebar:
        st.markdown("**" + style.safe(customer["name"]) + "**", unsafe_allow_html=True)
        st.caption(customer["locality"] + " · customer #" + str(customer["customer_id"]))
        st.button("Sign out", on_click=sign_out, width="stretch", key="sidebar_signout")
        st.markdown("---")
        developer = st.toggle("Developer mode", key="developer", help="Shows the technical ADBMS pages (concurrency lab, query lab, DBA console and more)")
        if developer:
            spatial_engine = "PostGIS (GiST index)"
            if not database.has_postgis():
                spatial_engine = "Haversine function"
            collection, mode, error = tracking.get_store()
            st.caption("PostgreSQL connected · " + spatial_engine + " · " + mode)
            with st.expander("Database tools"):
                if st.button("Rebuild database", width="stretch"):
                    with st.spinner("Rebuilding..."):
                        loader.build_database()
                    sign_out()
                    st.rerun()
                if st.button("Re-sync MongoDB", width="stretch"):
                    count = tracking.sync_from_postgres()
                    st.success(str(count) + " documents synced")


ok, error_text = database.can_connect()
if not ok:
    setup_screen(error_text)
if not database.is_ready():
    build_screen()
tracking.ensure_synced()

assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
st.logo(os.path.join(assets, "logo.svg"), size="large", icon_image=os.path.join(assets, "icon.svg"))

if "customer" not in st.session_state:
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl']{display:none}</style>", unsafe_allow_html=True)
    login.show()
    st.stop()

nav.pages["discover"] = st.Page(discover.show, title="Discover", icon=":material/restaurant:", url_path="discover", default=True)
nav.pages["menu"] = st.Page(menu.show, title="Menu", icon=":material/menu_book:", url_path="menu", visibility="hidden")
nav.pages["checkout"] = st.Page(checkout.show, title="Checkout", icon=":material/shopping_cart:", url_path="checkout", visibility="hidden")
nav.pages["track"] = st.Page(trackorder.show, title="Track order", icon=":material/delivery_dining:", url_path="track")
nav.pages["orders"] = st.Page(myorders.show, title="My orders", icon=":material/receipt_long:", url_path="orders")
nav.pages["account"] = st.Page(account.show, title="Account", icon=":material/person:", url_path="account")

structure = list(nav.pages.values())
if st.session_state.get("developer"):
    structure = {
        "FoodFlow": list(nav.pages.values()),
        "Developer · Overview": [
            st.Page(home.show, title="Home", icon=":material/space_dashboard:", url_path="home"),
            st.Page(design.show, title="Dataset & Design", icon=":material/schema:", url_path="design"),
        ],
        "Developer · Core ADBMS": [
            st.Page(ordering.show, title="Place Order · ACID", icon=":material/shopping_bag:", url_path="transactions"),
            st.Page(concurrencylab.show, title="Concurrency Lab", icon=":material/sync_lock:", url_path="concurrency"),
            st.Page(livetracking.show, title="Live Tracking · MongoDB", icon=":material/route:", url_path="tracking"),
            st.Page(maps.show, title="Delivery Map · GIS", icon=":material/map:", url_path="spatial"),
            st.Page(temporaldata.show, title="Temporal Data", icon=":material/history:", url_path="temporal"),
        ],
        "Developer · Evidence": [
            st.Page(querylab.show, title="Query Lab", icon=":material/terminal:", url_path="queries"),
            st.Page(dbaconsole.show, title="DBA Console", icon=":material/admin_panel_settings:", url_path="dba"),
        ],
    }
navigation = st.navigation(structure, position="top")
sidebar()
navigation.run()
