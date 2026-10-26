import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

from core import database
from core import spatial
from core import style

ORANGE = [232, 83, 43, 220]
GREY = [138, 123, 109, 90]
TEAL = [42, 157, 143, 230]
INK = [30, 27, 24, 255]


def show():
    engine = spatial.engine()
    style.hero("Rubric 3D · Spatial / GIS queries",
               "Who can deliver to me, and who should ride?",
               "Restaurants, customers and riders all have coordinates. Radius search, nearest-neighbour search and coverage analysis run as SQL inside PostgreSQL.",
               ["Spatial engine: " + engine, "Radius search", "K nearest neighbours", "Great-circle distance", "Spatial join", "Density heatmap"])

    customers = database.fetch("SELECT customer_id, name, locality, latitude, longitude FROM customer ORDER BY locality, name")
    cuisines = database.fetch("SELECT DISTINCT cuisine FROM restaurant ORDER BY cuisine")["cuisine"].tolist()

    style.section("01", "Restaurants within delivery radius")
    left, middle, right = st.columns([2, 1, 1])
    labels = {}
    for row in customers.to_dict("records"):
        labels[row["locality"] + " · " + row["name"] + " (#" + str(row["customer_id"]) + ")"] = row
    pick = left.selectbox("Customer location", list(labels.keys()), index=300)
    radius = middle.slider("Radius (km)", 0.5, 8.0, 3.0, 0.5)
    cuisine = right.selectbox("Cuisine", ["Any"] + cuisines)
    customer = labels[pick]
    lat = float(customer["latitude"])
    lon = float(customer["longitude"])

    chosen_cuisine = None
    if cuisine != "Any":
        chosen_cuisine = cuisine
    found, sql, elapsed = spatial.restaurants_within(lat, lon, radius, chosen_cuisine)
    partners, partner_sql, partner_elapsed = spatial.nearest_partners(lat, lon, 5)
    everything = spatial.all_restaurants()

    found_ids = set(found["restaurant_id"].tolist()) if len(found) > 0 else set()
    everything["color"] = everything["restaurant_id"].apply(lambda value: ORANGE if value in found_ids else GREY)
    everything["size"] = everything["restaurant_id"].apply(lambda value: 140 if value in found_ids else 80)
    everything["latitude"] = everything["latitude"].astype(float)
    everything["longitude"] = everything["longitude"].astype(float)
    partners["latitude"] = partners["latitude"].astype(float)
    partners["longitude"] = partners["longitude"].astype(float)
    here = pd.DataFrame([{"latitude": lat, "longitude": lon, "name": customer["name"] + " (customer)"}])

    zoom = 13
    if radius > 3:
        zoom = 12
    if radius > 5:
        zoom = 11
    deck = pdk.Deck(
        map_style="light",
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom, pitch=0),
        layers=[
            pdk.Layer("ScatterplotLayer", here, get_position=["longitude", "latitude"], get_radius=radius * 1000,
                      filled=True, stroked=True, get_fill_color=[232, 83, 43, 25], get_line_color=[232, 83, 43, 200], line_width_min_pixels=2),
            pdk.Layer("ScatterplotLayer", everything, get_position=["longitude", "latitude"], get_fill_color="color", get_radius="size", pickable=True),
            pdk.Layer("ScatterplotLayer", partners, get_position=["longitude", "latitude"], get_fill_color=TEAL, get_radius=110, pickable=True),
            pdk.Layer("ScatterplotLayer", here, get_position=["longitude", "latitude"], get_fill_color=INK, get_radius=150, pickable=True),
        ],
        tooltip={"html": "<b>{name}</b><br/>{cuisine} {vehicle}", "style": {"backgroundColor": "#1E1B18", "color": "#FBF7F2"}},
    )
    st.pydeck_chart(deck, height=480)
    st.caption("Black dot: customer · Orange: restaurants inside the radius · Grey: outside · Teal: 5 nearest available riders")

    style.kpis([("Restaurants in reach", str(len(found)), "within " + str(radius) + " km"),
                ("Closest", (str(found.iloc[0]["distance_km"]) + " km") if len(found) > 0 else "-", found.iloc[0]["name"] if len(found) > 0 else "none in range"),
                ("Nearest free rider", (str(partners.iloc[0]["distance_km"]) + " km") if len(partners) > 0 else "-", partners.iloc[0]["name"] if len(partners) > 0 else ""),
                ("Query time", str(round(elapsed, 1)) + " ms", engine)])
    st.write("")
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Radius query**")
        st.code(sql.strip(), language="sql")
        st.dataframe(found.drop(columns=["latitude", "longitude"]), hide_index=True, width="stretch", height=260)
    with right:
        st.markdown("**Nearest available delivery partners (KNN)**")
        st.code(partner_sql.strip(), language="sql")
        st.dataframe(partners.drop(columns=["latitude", "longitude"]), hide_index=True, width="stretch")

    if engine == "PostGIS":
        st.info("PostGIS is active: ST_DWithin uses the GiST index on geography(Point, 4326) and `<->` performs index-assisted nearest-neighbour search.")
    else:
        st.info("PostGIS is not installed on this server, so FoodFlow uses its own SQL function distance_km() (haversine formula) plus a bounding-box prefilter "
                "on a B-tree index of (latitude, longitude). Run with the PostGIS Docker image or Supabase/Neon to switch to ST_DWithin automatically.")

    style.section("02", "Where are the orders coming from?", "3D hexagon density of the latest delivered orders, by customer location.")
    points = spatial.delivery_points()
    points["latitude"] = points["latitude"].astype(float)
    points["longitude"] = points["longitude"].astype(float)
    deck = pdk.Deck(
        map_style="light",
        initial_view_state=pdk.ViewState(latitude=19.08, longitude=72.87, zoom=10.4, pitch=45, bearing=-10),
        layers=[pdk.Layer("HexagonLayer", points, get_position=["longitude", "latitude"], radius=550, elevation_scale=5,
                          elevation_range=[0, 1500], extruded=True, coverage=0.9, pickable=True,
                          color_range=[[253, 208, 162], [250, 170, 110], [242, 130, 70], [232, 83, 43], [180, 50, 20], [110, 30, 10]])],
        tooltip={"text": "{elevationValue} orders"},
    )
    st.pydeck_chart(deck, height=460)

    style.section("03", "Delivery coverage by locality", "A spatial join: for every customer, count restaurants within the radius, then average per locality. Low numbers show where to onboard new restaurants.")
    coverage_radius = st.slider("Coverage radius (km)", 1.0, 5.0, 2.0, 0.5, key="coverage")
    coverage, coverage_sql, coverage_ms = spatial.coverage_by_locality(coverage_radius)
    left, right = st.columns([3, 2])
    figure = px.bar(coverage, x="avg_restaurants_in_reach", y="locality", orientation="h", title="Average restaurants in reach per customer")
    figure.update_traces(marker_color=style.ORANGE)
    figure.update_layout(height=620, yaxis_title=None, xaxis_title=None)
    left.plotly_chart(figure, width="stretch")
    with right:
        st.code(coverage_sql.strip(), language="sql")
        st.caption("Ran in " + str(round(coverage_ms, 1)) + " ms across " + style.number(coverage["customers"].sum()) + " customers × 120 restaurants")
    style.footer()
