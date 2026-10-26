import os

import streamlit as st

st.set_page_config(page_title="FoodFlow · Hybrid ADBMS", page_icon="🍲", layout="wide", initial_sidebar_state="expanded")

from core import database
from core import loader
from core import style
from core import tracking
from views import home, design, ordering, concurrencylab, livetracking, maps, temporaldata, querylab, dbaconsole

style.apply_theme()


def setup_screen(error_text):
    style.hero("Setup needed", "FoodFlow can't reach PostgreSQL yet",
               "Start the databases with Docker or point DATABASE_URL to your own PostgreSQL server, then refresh this page.")
    st.code(error_text, language="text")
    st.markdown("**Quick start with Docker**")
    st.code("docker compose up -d\nstreamlit run app.py", language="bash")
    st.markdown("**Or set your own connection string in a `.env` file**")
    st.code("DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/foodflow\nMONGO_URI=mongodb://localhost:27017", language="bash")
    st.stop()


def build_screen():
    style.hero("First run", "Let's build the FoodFlow database",
               "This creates 11 tables, loads about 1.6 lakh rows of the Mumbai food delivery dataset, adds triggers, indexes, roles and row level security, then syncs tracking documents into MongoDB.",
               ["~30 seconds", "Runs once", "Safe to re-run"])
    if st.button("Build the database now", type="primary"):
        box = st.status("Building FoodFlow...", expanded=True)
        def show_progress(text):
            box.write(text)
        loader.build_database(progress=show_progress)
        box.update(label="Database ready", state="complete")
        st.rerun()
    st.stop()


def sidebar_footer():
    with st.sidebar:
        st.markdown("---")
        spatial_engine = "PostGIS (GiST index)"
        if not database.has_postgis():
            spatial_engine = "Haversine function"
        collection, mode, error = tracking.get_store()
        mongo_color = "#2A9D8F"
        if mode != "MongoDB":
            mongo_color = "#F2A541"
        st.markdown('<div class="ff-status"><b>Relational</b><span class="ff-dot" style="background:#2A9D8F"></span>PostgreSQL connected</div>'
                    '<div class="ff-status"><b>Spatial engine</b><span class="ff-dot" style="background:#2A9D8F"></span>' + spatial_engine + '</div>'
                    '<div class="ff-status"><b>Document store</b><span class="ff-dot" style="background:' + mongo_color + '"></span>' + mode + "</div>",
                    unsafe_allow_html=True)
        with st.expander("Database tools"):
            st.caption("Rebuild drops every table and reloads the dataset.")
            if st.button("Rebuild database", width="stretch"):
                with st.spinner("Rebuilding..."):
                    loader.build_database()
                st.success("Rebuilt")
            if st.button("Re-sync MongoDB", width="stretch"):
                with st.spinner("Syncing..."):
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

pages = {
    "Overview": [
        st.Page(home.show, title="Home", icon=":material/space_dashboard:", url_path="home", default=True),
        st.Page(design.show, title="Dataset & Design", icon=":material/schema:", url_path="design"),
    ],
    "Core ADBMS": [
        st.Page(ordering.show, title="Place Order · ACID", icon=":material/shopping_bag:", url_path="transactions"),
        st.Page(concurrencylab.show, title="Concurrency Lab", icon=":material/sync_lock:", url_path="concurrency"),
        st.Page(livetracking.show, title="Live Tracking · MongoDB", icon=":material/route:", url_path="tracking"),
        st.Page(maps.show, title="Delivery Map · GIS", icon=":material/map:", url_path="spatial"),
        st.Page(temporaldata.show, title="Temporal Data", icon=":material/history:", url_path="temporal"),
    ],
    "Evidence": [
        st.Page(querylab.show, title="Query Lab", icon=":material/terminal:", url_path="queries"),
        st.Page(dbaconsole.show, title="DBA Console", icon=":material/admin_panel_settings:", url_path="dba"),
    ],
}

navigation = st.navigation(pages)
sidebar_footer()
navigation.run()
