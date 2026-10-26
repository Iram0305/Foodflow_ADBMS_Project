import plotly.express as px
import streamlit as st

from core import database
from core import queries
from core import style


def draw_chart(query, frame):
    chart = query["chart"]
    if chart is None or len(frame) == 0:
        return
    kind, x, y = chart
    if kind == "bar":
        data = frame.copy()
        if data[x].dtype == object and len(data) > 1:
            figure = px.bar(data.iloc[::-1], x=y, y=x, orientation="h")
            figure.update_layout(height=max(300, 28 * len(data)), yaxis_title=None, xaxis_title=y)
        else:
            figure = px.bar(data, x=x, y=y)
            figure.update_layout(height=340, xaxis_title=x, yaxis_title=y)
        figure.update_traces(marker_color=style.ORANGE)
    else:
        figure = px.line(frame, x=x, y=y)
        figure.update_layout(height=340, xaxis_title=None, yaxis_title=None, legend_title=None, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(figure, width="stretch")


def show():
    style.hero("Rubric 4 · Queries & evidence",
               str(len(queries.QUERIES)) + " meaningful queries, executed live",
               "Each query shows the business question, the SQL concept it demonstrates, the SQL itself, the live output and how long PostgreSQL took. "
               "Screenshot any card for the report.",
               queries.categories())

    category = st.pills("Category", ["All"] + queries.categories(), default="All")
    chosen = []
    for query in queries.QUERIES:
        if category in [None, "All"] or query["category"] == category:
            chosen.append(query)

    run_all = st.toggle("Run every query on this page", value=False)
    number = 1
    for query in chosen:
        st.markdown("---")
        top_left, top_right = st.columns([4, 1])
        top_left.markdown("#### Q" + str(number) + ". " + query["title"])
        top_left.caption(query["question"])
        top_right.markdown('<span class="ff-chip ff-chip-light">' + query["category"] + "</span>", unsafe_allow_html=True)
        st.caption("Concept: " + query["concept"])
        left, right = st.columns([2, 3])
        with left:
            st.code(query["sql"], language="sql")
        with right:
            if run_all or st.button("Run Q" + str(number), key="run_" + query["title"]):
                frame, elapsed = database.run_query(query["sql"])
                st.caption(style.number(len(frame)) + " rows · " + str(round(elapsed, 1)) + " ms")
                st.dataframe(frame, hide_index=True, width="stretch", height=min(400, 38 + 35 * len(frame)))
                draw_chart(query, frame)
        number += 1

    style.section("SQL", "Write your own query", "Runs inside a READ ONLY transaction with a 15 second timeout, so nothing can be changed or broken.")
    text = st.text_area("SQL", "SELECT r.locality, COUNT(*) AS orders\nFROM orders o JOIN restaurant r ON r.restaurant_id = o.restaurant_id\nGROUP BY r.locality\nORDER BY orders DESC;", height=150)
    if st.button("Execute", type="primary"):
        try:
            frame, elapsed = database.run_readonly(text)
            st.caption(style.number(len(frame)) + " rows · " + str(round(elapsed, 1)) + " ms")
            st.dataframe(frame, hide_index=True, width="stretch")
        except Exception as error:
            st.error(str(error).splitlines()[0])
    style.footer()
