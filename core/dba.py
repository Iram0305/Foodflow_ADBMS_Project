import json
import os
import shutil
import subprocess
from datetime import datetime

from core import config
from core import database
from core import loader

ROLES = ["ff_admin", "ff_restaurant_manager", "ff_delivery_partner", "ff_customer"]

ROLE_DESCRIPTIONS = {
    "ff_admin": "Full access to every table",
    "ff_restaurant_manager": "Manages menu and order status, read-only on customers",
    "ff_delivery_partner": "Sees assigned deliveries, can update pickup/delivery times and own location",
    "ff_customer": "Reads menus and only their own orders (row level security)",
}

PERMISSION_TESTS = [
    ("Customer reads restaurants", "ff_customer", "SELECT name, cuisine, rating FROM restaurant ORDER BY rating DESC LIMIT 5;"),
    ("Customer reads orders (RLS filters to own rows)", "ff_customer", "SELECT order_id, customer_id, status, total_amount FROM orders ORDER BY order_time DESC LIMIT 10;"),
    ("Customer tries to change a price", "ff_customer", "UPDATE menu_item SET price = 1 WHERE item_id = 1001;"),
    ("Customer tries to read delivery partners", "ff_customer", "SELECT name, phone FROM delivery_partner LIMIT 5;"),
    ("Restaurant manager updates stock", "ff_restaurant_manager", "UPDATE menu_item SET stock = stock + 10 WHERE item_id = 1001;"),
    ("Restaurant manager tries to delete a payment", "ff_restaurant_manager", "DELETE FROM payment WHERE payment_id = 1;"),
    ("Delivery partner marks themself available", "ff_delivery_partner", "UPDATE delivery_partner SET is_available = TRUE WHERE partner_id = 1;"),
    ("Delivery partner tries to read order totals", "ff_delivery_partner", "SELECT order_id, total_amount FROM orders LIMIT 5;"),
    ("Admin reads payments", "ff_admin", "SELECT method, status, amount FROM payment LIMIT 5;"),
]

INDEX_CASES = {
    "Orders of one customer": {
        "index": "idx_orders_customer",
        "create": "CREATE INDEX idx_orders_customer ON orders(customer_id);",
        "query": "SELECT * FROM orders WHERE customer_id = 101;",
    },
    "Status history of one order": {
        "index": "idx_history_order",
        "create": "CREATE INDEX idx_history_order ON order_status_history(order_id);",
        "query": "SELECT * FROM order_status_history WHERE order_id = 110000;",
    },
    "Orders placed in the last 24 hours": {
        "index": "idx_orders_time",
        "create": "CREATE INDEX idx_orders_time ON orders(order_time);",
        "query": "SELECT * FROM orders WHERE order_time >= NOW() - INTERVAL '1 day';",
    },
}

BACKUP_TABLES = ["customer", "restaurant", "menu_item", "menu_price_history", "delivery_partner", "orders",
                 "order_item", "order_status_history", "payment", "delivery", "review"]


def role_privileges():
    sql = """
SELECT grantee AS role, table_name, STRING_AGG(DISTINCT privilege_type, ', ') AS privileges
FROM information_schema.role_table_grants
WHERE grantee LIKE 'ff_%%'
GROUP BY grantee, table_name
ORDER BY grantee, table_name;"""
    return database.fetch(sql)


def column_privileges():
    sql = """
SELECT grantee AS role, table_name, STRING_AGG(column_name || ' (' || privilege_type || ')', ', ') AS columns
FROM information_schema.column_privileges
WHERE grantee IN ('ff_delivery_partner')
GROUP BY grantee, table_name
ORDER BY table_name;"""
    return database.fetch(sql)


def policies():
    return database.fetch("SELECT policyname, tablename, roles::text AS roles, cmd, qual FROM pg_policies ORDER BY tablename")


def run_as_role(role, sql, customer_id=None):
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    try:
        if customer_id is not None:
            cursor.execute("SELECT set_config('app.customer_id', %s, TRUE)", (str(int(customer_id)),))
        cursor.execute("SET LOCAL ROLE " + role)
        cursor.execute(sql)
        if cursor.description is not None:
            columns = []
            for column in cursor.description:
                columns.append(column[0])
            rows = cursor.fetchall()
            import pandas as pd
            return True, pd.DataFrame(rows, columns=columns), "Allowed"
        return True, None, "Allowed: " + str(cursor.rowcount) + " row(s) affected (rolled back after the test)"
    except Exception as error:
        return False, None, str(error).splitlines()[0]
    finally:
        connection.rollback()
        connection.close()


def explain(sql):
    frame = database.fetch("EXPLAIN (ANALYZE, BUFFERS) " + sql)
    lines = []
    for value in frame.iloc[:, 0].tolist():
        lines.append(value)
    return "\n".join(lines)


def plan_time(plan_text):
    for line in plan_text.splitlines():
        if "Execution Time" in line:
            return float(line.split(":")[1].replace("ms", "").strip())
    return None


def compare_index(case_name):
    case = INDEX_CASES[case_name]
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.execute("DROP INDEX IF EXISTS " + case["index"])
        cursor.execute("EXPLAIN (ANALYZE, BUFFERS) " + case["query"])
        without_rows = cursor.fetchall()
        connection.rollback()
    finally:
        connection.close()
    without_plan = ""
    for row in without_rows:
        without_plan = without_plan + row[0] + "\n"
    with_plan = explain(case["query"])
    return {"query": case["query"], "create": case["create"], "index": case["index"],
            "without_plan": without_plan.strip(), "with_plan": with_plan,
            "without_ms": plan_time(without_plan), "with_ms": plan_time(with_plan)}


def list_indexes():
    sql = """
SELECT s.relname AS table_name, s.indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size,
       s.idx_scan AS times_used,
       i.indexdef AS definition
FROM pg_stat_user_indexes s
JOIN pg_indexes i ON i.indexname = s.indexrelname
ORDER BY s.relname, s.indexrelname;"""
    return database.fetch(sql)


def make_backup(label="manual"):
    stamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    folder = os.path.join(config.BACKUP_FOLDER, stamp + " " + label)
    os.makedirs(folder, exist_ok=True)
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    counts = {}
    try:
        cursor.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for table in BACKUP_TABLES:
            path = os.path.join(folder, table + ".csv")
            with open(path, "w", encoding="utf-8") as f:
                cursor.copy_expert("COPY " + table + " TO STDOUT WITH (FORMAT csv, HEADER true)", f)
            cursor.execute("SELECT COUNT(*) FROM " + table)
            counts[table] = cursor.fetchone()[0]
        connection.rollback()
    finally:
        connection.close()
    manifest = {"created": stamp, "label": label, "tables": counts}
    with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return folder, counts


def list_backups():
    if not os.path.exists(config.BACKUP_FOLDER):
        return []
    found = []
    for name in sorted(os.listdir(config.BACKUP_FOLDER), reverse=True):
        manifest_path = os.path.join(config.BACKUP_FOLDER, name, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            manifest["folder"] = os.path.join(config.BACKUP_FOLDER, name)
            manifest["name"] = name
            found.append(manifest)
    return found


def table_counts():
    counts = {}
    for table in BACKUP_TABLES:
        counts[table] = database.fetch_value("SELECT COUNT(*) FROM " + table)
    return counts


DISASTERS = {
    "Accidental DELETE of every review": "DELETE FROM review;",
    "Ransomware wipes payments and deliveries": "DELETE FROM payment; DELETE FROM delivery;",
    "Bad script sets every menu price to 1": "UPDATE menu_item SET price = 1;",
}


def cause_disaster(name):
    database.execute(DISASTERS[name])


def restore_backup(folder):
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.execute("ALTER TABLE review DISABLE TRIGGER trg_review_rating")
        cursor.execute("ALTER TABLE menu_item DISABLE TRIGGER trg_price_history")
        cursor.execute("ALTER TABLE orders DISABLE TRIGGER trg_status_history")
        cursor.execute("TRUNCATE " + ", ".join(BACKUP_TABLES) + " CASCADE")
        for table in BACKUP_TABLES:
            with open(os.path.join(folder, table + ".csv"), encoding="utf-8") as f:
                cursor.copy_expert("COPY " + table + " FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        cursor.execute("ALTER TABLE review ENABLE TRIGGER trg_review_rating")
        cursor.execute("ALTER TABLE menu_item ENABLE TRIGGER trg_price_history")
        cursor.execute("ALTER TABLE orders ENABLE TRIGGER trg_status_history")
        cursor.execute("SELECT setval('orders_order_id_seq', (SELECT MAX(order_id) FROM orders))")
        cursor.execute("SELECT setval('payment_payment_id_seq', GREATEST((SELECT MAX(payment_id) FROM payment), 1))")
        cursor.execute("SELECT setval('review_review_id_seq', GREATEST((SELECT MAX(review_id) FROM review), 1))")
        cursor.execute("SELECT setval('order_status_history_history_id_seq', (SELECT MAX(history_id) FROM order_status_history))")
        cursor.execute("SELECT setval('menu_price_history_history_id_seq', (SELECT MAX(history_id) FROM menu_price_history))")
        connection.commit()
    except Exception as error:
        connection.rollback()
        connection.close()
        return False, str(error).splitlines()[0]
    connection.close()
    database.execute("REFRESH MATERIALIZED VIEW restaurant_stats")
    try:
        from core import tracking
        tracking.sync_from_postgres()
    except Exception:
        pass
    return True, "Restored all tables in a single transaction"


def pg_dump_available():
    return shutil.which("pg_dump") is not None


def run_pg_dump():
    stamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    os.makedirs(config.BACKUP_FOLDER, exist_ok=True)
    path = os.path.join(config.BACKUP_FOLDER, "foodflow " + stamp + ".sql")
    result = subprocess.run(["pg_dump", "--no-owner", "--no-privileges", "-f", path, config.postgres_url()],
                            capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return False, result.stderr.strip()[:300]
    return True, path


def database_overview():
    sql = """
SELECT current_database() AS database,
       pg_size_pretty(pg_database_size(current_database())) AS size,
       (SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()) AS connections,
       (SELECT setting FROM pg_settings WHERE name = 'max_connections') AS max_connections,
       split_part(version(), ' on ', 1) AS version,
       NOW() - pg_postmaster_start_time() AS uptime;"""
    return database.fetch(sql)


def transaction_stats():
    sql = """
SELECT xact_commit AS commits, xact_rollback AS rollbacks, deadlocks, conflicts,
       tup_inserted AS rows_inserted, tup_updated AS rows_updated, tup_deleted AS rows_deleted,
       ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_percent
FROM pg_stat_database
WHERE datname = current_database();"""
    return database.fetch(sql)


def table_sizes():
    sql = """
SELECT relname AS table_name,
       n_live_tup AS live_rows,
       n_dead_tup AS dead_rows,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
       pg_total_relation_size(relid) AS size_bytes,
       seq_scan, idx_scan,
       last_autovacuum, last_analyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;"""
    return database.fetch(sql)


def active_sessions():
    sql = """
SELECT pid, usename AS user_name, application_name, state,
       ROUND(EXTRACT(EPOCH FROM (NOW() - query_start))::numeric, 2) AS running_seconds,
       wait_event_type, LEFT(query, 90) AS query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start DESC NULLS LAST;"""
    return database.fetch(sql)


def current_locks():
    sql = """
SELECT l.locktype, c.relname AS relation, l.mode, l.granted, a.pid, LEFT(a.query, 60) AS query
FROM pg_locks l
LEFT JOIN pg_class c ON c.oid = l.relation
LEFT JOIN pg_stat_activity a ON a.pid = l.pid
WHERE a.datname = current_database() AND c.relname NOT LIKE 'pg_%%'
ORDER BY l.granted, c.relname;"""
    return database.fetch(sql)


def run_maintenance(task):
    if task == "VACUUM ANALYZE":
        database.execute("VACUUM ANALYZE")
    elif task == "REFRESH MATERIALIZED VIEW":
        database.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY restaurant_stats")
    elif task == "REINDEX orders":
        database.execute("REINDEX TABLE orders")
    return True
