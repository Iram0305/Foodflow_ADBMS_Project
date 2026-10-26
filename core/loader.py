import os

from core import config
from core import database
from core import generator

TABLE_FILES = [
    ("customer", "customers", "customer_id, name, phone, email, address, locality, latitude, longitude, joined_on"),
    ("restaurant", "restaurants", "restaurant_id, name, cuisine, locality, address, latitude, longitude, rating, cost_for_two, opens_at, closes_at, is_veg"),
    ("menu_item", "menu_items", "item_id, restaurant_id, item_name, category, price, stock, is_veg"),
    ("menu_price_history", "menu_price_history", "item_id, price, valid_from, valid_to"),
    ("delivery_partner", "delivery_partners", "partner_id, name, phone, vehicle, latitude, longitude, is_available, rating, joined_on"),
    ("orders", "orders", "order_id, customer_id, restaurant_id, order_time, status, total_amount"),
    ("order_item", "order_items", "order_id, item_id, quantity, unit_price"),
    ("order_status_history", "order_status_history", "order_id, status, changed_at"),
    ("payment", "payments", "order_id, amount, method, status, paid_at"),
    ("delivery", "deliveries", "order_id, partner_id, pickup_time, delivered_time, distance_km"),
    ("review", "reviews", "order_id, customer_id, restaurant_id, stars, comment, reviewed_at"),
]

TIME_COLUMNS = [
    ("orders", ["order_time"]),
    ("order_status_history", ["changed_at"]),
    ("payment", ["paid_at"]),
    ("delivery", ["pickup_time", "delivered_time"]),
    ("review", ["reviewed_at"]),
    ("menu_price_history", ["valid_from", "valid_to"]),
]

DATE_COLUMNS = [
    ("customer", "joined_on"),
    ("delivery_partner", "joined_on"),
]


def read_sql_file(name):
    with open(os.path.join(config.SQL_FOLDER, name), encoding="utf-8") as f:
        return f.read()


def dataset_exists():
    for table, file_name, columns in TABLE_FILES:
        if not os.path.exists(os.path.join(config.DATA_FOLDER, file_name + ".csv")):
            return False
    return True


def build_database(progress=None, regenerate=False):
    messages = []

    def say(text):
        messages.append(text)
        if progress is not None:
            progress(text)

    if regenerate or not dataset_exists():
        say("Generating synthetic dataset CSV files")
        generator.generate(config.DATA_FOLDER)

    connection = database.connect(autocommit=False)
    cursor = connection.cursor()

    say("Creating relational schema (11 tables with keys and constraints)")
    cursor.execute(read_sql_file("schema.sql"))

    for table, file_name, columns in TABLE_FILES:
        say("Loading " + file_name + ".csv into " + table)
        with open(os.path.join(config.DATA_FOLDER, file_name + ".csv"), encoding="utf-8") as f:
            cursor.copy_expert("COPY " + table + " (" + columns + ") FROM STDIN WITH (FORMAT csv, HEADER true)", f)

    say("Aligning dataset timeline with the current time")
    cursor.execute("SELECT date_trunc('second', NOW()::timestamp - MAX(order_time)) FROM orders")
    gap = cursor.fetchone()[0]
    for table, columns in TIME_COLUMNS:
        parts = []
        for column in columns:
            parts.append(column + " = " + column + " + %s")
        values = []
        for column in columns:
            values.append(gap)
        cursor.execute("UPDATE " + table + " SET " + ", ".join(parts), values)
    for table, column in DATE_COLUMNS:
        cursor.execute("UPDATE " + table + " SET " + column + " = " + column + " + %s", (gap.days,))

    cursor.execute("SELECT setval('orders_order_id_seq', (SELECT MAX(order_id) FROM orders))")
    cursor.execute("SELECT setval('payment_payment_id_seq', (SELECT MAX(payment_id) FROM payment))")
    cursor.execute("SELECT setval('review_review_id_seq', (SELECT MAX(review_id) FROM review))")

    say("Creating functions, triggers and materialized view")
    cursor.execute(read_sql_file("functions.sql"))

    say("Creating indexes")
    cursor.execute(read_sql_file("indexes.sql"))
    connection.commit()

    say("Trying to enable PostGIS")
    try:
        cursor.execute(read_sql_file("postgis.sql"))
        connection.commit()
        say("PostGIS enabled with GiST spatial indexes")
    except Exception:
        connection.rollback()
        say("PostGIS not available, using the haversine distance_km() function instead")

    say("Creating roles, privileges and row level security")
    try:
        cursor.execute(read_sql_file("security.sql"))
        connection.commit()
    except Exception as error:
        connection.rollback()
        say("Could not create roles on this server: " + str(error).splitlines()[0])

    for role in ["ff_admin", "ff_restaurant_manager", "ff_delivery_partner", "ff_customer"]:
        try:
            cursor.execute("GRANT " + role + " TO CURRENT_USER")
            connection.commit()
        except Exception:
            connection.rollback()

    connection.autocommit = True
    cursor.execute("ANALYZE")
    cursor.execute("REFRESH MATERIALIZED VIEW restaurant_stats")
    connection.close()

    say("Syncing order tracking documents into MongoDB")
    from core import tracking
    count = tracking.sync_from_postgres()
    say("Inserted " + str(count) + " tracking documents")
    say("Done")
    return messages


if __name__ == "__main__":
    import sys
    regenerate = "--regenerate" in sys.argv
    build_database(progress=print, regenerate=regenerate)
