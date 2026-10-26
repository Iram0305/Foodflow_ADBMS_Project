import os

import pandas as pd
import plotly.express as px
import streamlit as st

from core import config
from core import dba
from core import style


def security_tab():
    st.markdown("Four roles follow the principle of least privilege. Row level security makes sure a customer only ever sees their own orders.")
    columns = st.columns(4)
    for i in range(4):
        with columns[i]:
            style.card(dba.ROLES[i], dba.ROLE_DESCRIPTIONS[dba.ROLES[i]])
    privileges = dba.role_privileges()
    if len(privileges) > 0:
        grid = privileges.pivot(index="table_name", columns="role", values="privileges").fillna("-")
        st.markdown("**Privilege matrix (from information_schema.role_table_grants)**")
        st.dataframe(grid, width="stretch")
    columns_frame = dba.column_privileges()
    if len(columns_frame) > 0:
        st.markdown("**Column-level privileges for delivery partners**")
        st.dataframe(columns_frame, hide_index=True, width="stretch")
    st.markdown("**Row level security policies**")
    st.dataframe(dba.policies(), hide_index=True, width="stretch")
    with st.expander("SQL used to set this up"):
        with open(os.path.join(config.SQL_FOLDER, "security.sql"), encoding="utf-8") as f:
            st.code(f.read(), language="sql")

    style.section("TEST", "Try it: run a statement as a role", "Runs with SET LOCAL ROLE inside a transaction that is always rolled back.")
    tests = {}
    for label, role, sql in dba.PERMISSION_TESTS:
        tests[label] = (role, sql)
    left, right = st.columns([2, 1])
    pick = left.selectbox("Scenario", list(tests.keys()), index=1)
    customer_id = right.number_input("app.customer_id (for RLS)", min_value=1, max_value=1500, value=101)
    role, sql = tests[pick]
    sql = st.text_area("Statement", sql, key="perm_sql_" + pick)
    st.code("BEGIN;\nSELECT set_config('app.customer_id', '" + str(customer_id) + "', true);\nSET LOCAL ROLE " + role + ";\n" + sql + "\nROLLBACK;", language="sql")
    if st.button("Run as " + role, type="primary"):
        ok, frame, message = dba.run_as_role(role, sql, customer_id)
        if ok:
            style.banner("good", "✅", "Allowed", message)
            if frame is not None:
                st.dataframe(frame, hide_index=True, width="stretch")
                if "customer_id" in frame.columns:
                    st.caption("Distinct customer_id values returned: " + str(sorted(frame["customer_id"].unique().tolist())))
        else:
            style.banner("bad", "⛔", "Blocked by PostgreSQL", message)


def indexing_tab():
    st.markdown("Each comparison drops the index **inside a transaction**, runs EXPLAIN ANALYZE, then rolls back (DDL is transactional in PostgreSQL), and runs it again with the index.")
    case = st.selectbox("Query to optimise", list(dba.INDEX_CASES.keys()))
    if st.button("Compare without vs with index", type="primary"):
        st.session_state["index_result"] = dba.compare_index(case)
    result = st.session_state.get("index_result")
    if result is not None:
        st.code(result["query"], language="sql")
        speed = "-"
        if result["without_ms"] and result["with_ms"]:
            speed = str(round(result["without_ms"] / max(result["with_ms"], 0.001), 1)) + "x faster"
        style.kpis([("Without index", str(result["without_ms"]) + " ms", result["without_plan"].splitlines()[0].split("  ")[0]),
                    ("With " + result["index"], str(result["with_ms"]) + " ms", result["with_plan"].splitlines()[0].split("  ")[0]),
                    ("Speed-up", speed, result["create"])])
        st.write("")
        left, right = st.columns(2)
        left.markdown("**Plan without the index**")
        left.code(result["without_plan"], language="text")
        right.markdown("**Plan with the index**")
        right.code(result["with_plan"], language="text")
    st.markdown("**All indexes and how often the planner used them**")
    st.dataframe(dba.list_indexes(), hide_index=True, width="stretch", height=330)


def backup_tab():
    st.markdown("A consistent logical backup is taken inside a **REPEATABLE READ READ ONLY** transaction, so every table comes from the same snapshot even while orders keep arriving.")
    counts = dba.table_counts()
    left, right = st.columns([1, 2])
    with left:
        st.markdown("**Step 1 · Back up**")
        if st.button("Take a backup now", type="primary", width="stretch"):
            folder, saved = dba.make_backup("before demo")
            st.success("Saved " + style.number(sum(saved.values())) + " rows to backups/" + os.path.basename(folder))
        st.markdown("**Step 2 · Disaster**")
        disaster = st.selectbox("Simulate a failure", list(dba.DISASTERS.keys()))
        st.code(dba.DISASTERS[disaster], language="sql")
        if st.button("Cause the disaster", width="stretch"):
            dba.cause_disaster(disaster)
            st.error("Done. Look at the row counts.")
            counts = dba.table_counts()
        st.markdown("**Step 3 · Restore**")
        backups = dba.list_backups()
        names = []
        for backup in backups:
            names.append(backup["name"])
        chosen = st.selectbox("Backup to restore", names) if names else None
        if st.button("Restore selected backup", width="stretch", disabled=chosen is None):
            folder = None
            for backup in backups:
                if backup["name"] == chosen:
                    folder = backup["folder"]
            with st.spinner("Restoring in one transaction..."):
                ok, message = dba.restore_backup(folder)
            if ok:
                st.success(message)
            else:
                st.error(message)
            counts = dba.table_counts()
    with right:
        frame = pd.DataFrame({"table": list(counts.keys()), "rows now": list(counts.values())})
        backups = dba.list_backups()
        if backups:
            frame["rows in latest backup"] = frame["table"].apply(lambda name: backups[0]["tables"].get(name))
            frame["status"] = frame.apply(lambda row: "OK" if row["rows now"] == row["rows in latest backup"] else "DIFFERENT", axis=1)
        st.dataframe(frame, hide_index=True, width="stretch", height=430)

    style.section("PG_DUMP", "Physical tool: pg_dump")
    st.code('pg_dump --no-owner --no-privileges -f "foodflow backup.sql" "$DATABASE_URL"\npsql "$DATABASE_URL" -f "foodflow backup.sql"', language="bash")
    if dba.pg_dump_available():
        if st.button("Run pg_dump now"):
            ok, output = dba.run_pg_dump()
            if ok:
                size = os.path.getsize(output) / 1024 / 1024
                st.success("Wrote " + os.path.basename(output) + " (" + str(round(size, 2)) + " MB)")
                with open(output, "rb") as f:
                    st.download_button("Download SQL dump", f.read(), file_name=os.path.basename(output))
            else:
                st.error(output)
    else:
        st.caption("pg_dump is not installed where this app runs, so only the logical CSV backup is available here.")


def monitoring_tab():
    if st.button("Refresh"):
        st.rerun()
    overview = dba.database_overview().iloc[0]
    stats = dba.transaction_stats().iloc[0]
    style.kpis([("Database size", str(overview["size"]), str(overview["database"])),
                ("Connections", str(overview["connections"]) + " / " + str(overview["max_connections"]), "active sessions"),
                ("Cache hit ratio", str(stats["cache_hit_percent"]) + " %", "buffer cache"),
                ("Commits / rollbacks", style.number(stats["commits"]) + " / " + style.number(stats["rollbacks"]), str(stats["deadlocks"]) + " deadlocks detected")])
    st.caption(str(overview["version"]) + " · up for " + str(overview["uptime"]).split(".")[0])
    st.write("")
    sizes = dba.table_sizes()
    left, right = st.columns([2, 3])
    figure = px.bar(sizes.sort_values("size_bytes"), x="size_bytes", y="table_name", orientation="h", title="Table size including indexes")
    figure.update_traces(marker_color=style.ORANGE)
    figure.update_layout(height=380, yaxis_title=None, xaxis_title="bytes")
    left.plotly_chart(figure, width="stretch")
    right.markdown("**Table statistics**")
    right.dataframe(sizes.drop(columns=["size_bytes"]), hide_index=True, width="stretch", height=380)
    st.markdown("**Sessions (pg_stat_activity)**")
    st.dataframe(dba.active_sessions(), hide_index=True, width="stretch")
    st.markdown("**Locks held right now (pg_locks)**")
    locks = dba.current_locks()
    if len(locks) == 0:
        st.caption("No user-table locks at this moment. Run the Concurrency Lab in another tab and refresh to catch some.")
    else:
        st.dataframe(locks, hide_index=True, width="stretch")
    st.markdown("**Maintenance**")
    columns = st.columns(3)
    tasks = ["VACUUM ANALYZE", "REFRESH MATERIALIZED VIEW", "REINDEX orders"]
    for i in range(3):
        if columns[i].button(tasks[i], width="stretch"):
            dba.run_maintenance(tasks[i])
            st.success(tasks[i] + " finished")


def show():
    style.hero("Rubric 5 · DBA responsibilities",
               "Running the database like a DBA would",
               "Security with roles and row level security, indexing proven with EXPLAIN ANALYZE, a full backup → disaster → restore drill, and live monitoring from PostgreSQL's statistics views.",
               ["GRANT / REVOKE", "Row level security", "EXPLAIN ANALYZE", "Backup & restore", "pg_stat_activity", "VACUUM"])
    tabs = st.tabs(["Security", "Indexing", "Backup & recovery", "Monitoring"])
    with tabs[0]:
        security_tab()
    with tabs[1]:
        indexing_tab()
    with tabs[2]:
        backup_tab()
    with tabs[3]:
        monitoring_tab()
    style.footer()
