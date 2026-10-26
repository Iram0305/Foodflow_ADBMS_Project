import streamlit as st

from core import concurrency
from core import database
from core import style

EXPLAIN = {
    "No locking (unsafe)": ("Lost update", "Both customers read stock = 1 before either writes. Each writes 0 and both orders are confirmed: one pizza, two happy customers, one angry kitchen."),
    "Pessimistic locking (SELECT ... FOR UPDATE)": ("Row-level exclusive lock", "Customer A locks the row. Customer B's SELECT ... FOR UPDATE has to wait until A commits, then sees stock = 0 and is turned away."),
    "Optimistic locking (version column)": ("Compare-and-swap with a version number", "Nobody waits. When writing, each UPDATE checks the version it read is still current. B's version is stale so 0 rows match and B is rejected."),
    "SERIALIZABLE isolation": ("Strictest isolation level", "PostgreSQL detects that B's transaction would break serial order and aborts it with a serialization failure. The app would simply retry."),
}


def show():
    style.hero("Rubric 3B · Concurrency control",
               "Two customers, one last pizza",
               "Two real database connections run at the same moment in separate threads. Pick a concurrency strategy and see who gets the food.",
               ["Lost update", "Row locks", "Optimistic locking", "SERIALIZABLE", "Deadlock detection"])

    items = database.fetch("""
        SELECT m.item_id, m.item_name, r.name AS restaurant
        FROM menu_item m JOIN restaurant r ON r.restaurant_id = m.restaurant_id
        WHERE m.category IN ('Pizza', 'Biryani') ORDER BY r.name, m.item_name LIMIT 60
    """)
    labels = {}
    for row in items.to_dict("records"):
        labels[row["item_name"] + " · " + row["restaurant"]] = int(row["item_id"])

    style.section("01", "Race condition simulator")
    left, middle, right = st.columns([2, 2, 1])
    item_pick = left.selectbox("Item both customers want", list(labels.keys()))
    mode = middle.selectbox("Concurrency strategy", list(concurrency.MODES.keys()))
    stock = right.number_input("Starting stock", min_value=1, max_value=3, value=1)
    think = st.slider("Time each customer spends paying (seconds)", 0.3, 2.0, 1.0, 0.1)
    title, text = EXPLAIN[mode]
    style.chips([mode, title])
    st.caption(text)

    run_one, run_all = st.columns(2)
    if run_one.button("Run the race", type="primary", width="stretch"):
        with st.spinner("Two transactions running in parallel..."):
            st.session_state["race"] = concurrency.run_race(labels[item_pick], mode, int(stock), think)
            st.session_state["race_mode"] = mode
    if run_all.button("Compare all four strategies", width="stretch"):
        summary = []
        with st.spinner("Running four races..."):
            for label in concurrency.MODES:
                outcome = concurrency.run_race(labels[item_pick], label, int(stock), 0.5)
                summary.append({"strategy": label, "Customer A": outcome["results"].get("Customer A"), "Customer B": outcome["results"].get("Customer B"),
                                "units sold": outcome["units_sold"], "stock left": outcome["final_stock"],
                                "correct?": "No, oversold" if outcome["oversold"] else "Yes"})
        st.session_state["race_summary"] = summary

    if "race_summary" in st.session_state:
        st.dataframe(st.session_state["race_summary"], hide_index=True, width="stretch")

    race = st.session_state.get("race")
    if race is not None:
        if race["oversold"]:
            style.banner("bad", "⚠️", "Inconsistent: " + str(race["units_sold"]) + " sold, but only " + str(race["starting_stock"]) + " existed",
                         "Stock ended at " + str(race["final_stock"]) + ". This is the classic lost update anomaly.")
        else:
            style.banner("good", "🛡️", "Consistent: " + str(race["units_sold"]) + " sold from a stock of " + str(race["starting_stock"]),
                         "Stock ended at " + str(race["final_stock"]) + ". " + st.session_state["race_mode"] + " protected the data.")
        style.lanes(race["events"])
        st.caption("Stock was restored to " + str(race["restored_to"]) + " after the demo.")

    style.section("02", "Deadlock detection", "Customer A locks item X then wants Y. Customer B locks Y then wants X. Neither can continue, so PostgreSQL's deadlock detector aborts one of them after deadlock_timeout.")
    left, right = st.columns(2)
    keys = list(labels.keys())
    first = left.selectbox("Item X", keys, index=0)
    second = right.selectbox("Item Y", keys, index=min(1, len(keys) - 1))
    if st.button("Cause a deadlock", disabled=first == second):
        with st.spinner("Waiting for PostgreSQL to notice..."):
            st.session_state["deadlock"] = concurrency.run_deadlock(labels[first], labels[second])
    deadlock = st.session_state.get("deadlock")
    if deadlock is not None:
        victim = "nobody"
        for who in deadlock["results"]:
            if deadlock["results"][who] == "ABORTED":
                victim = who
        style.banner("warn", "🔁", "Deadlock detected and resolved", victim + " was chosen as the victim and rolled back so the other transaction could finish.")
        style.lanes(deadlock["events"])
        timeout = database.fetch_value("SHOW deadlock_timeout")
        st.caption("deadlock_timeout on this server: " + str(timeout))
    style.footer()
