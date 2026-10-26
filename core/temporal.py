from core import database

PRICE_HISTORY_SQL = """
SELECT price, valid_from, valid_to,
       CASE WHEN valid_to IS NULL THEN 'current' ELSE 'expired' END AS state
FROM menu_price_history
WHERE item_id = %(item_id)s
ORDER BY valid_from;"""

MENU_AS_OF_SQL = """
SELECT m.item_name, m.category, h.price AS price_then, m.price AS price_now,
       ROUND(((m.price - h.price) / h.price * 100)::numeric, 1) AS change_percent
FROM menu_item m
JOIN menu_price_history h ON h.item_id = m.item_id
WHERE m.restaurant_id = %(restaurant_id)s
  AND h.valid_from <= %(moment)s
  AND (h.valid_to IS NULL OR h.valid_to > %(moment)s)
ORDER BY m.category, m.item_name;"""

RECENT_CHANGES_SQL = """
SELECT m.item_name, r.name AS restaurant,
       LAG(h.price) OVER (PARTITION BY h.item_id ORDER BY h.valid_from) AS old_price,
       h.price AS new_price,
       h.valid_from AS changed_at
FROM menu_price_history h
JOIN menu_item m ON m.item_id = h.item_id
JOIN restaurant r ON r.restaurant_id = m.restaurant_id
ORDER BY h.valid_from DESC
LIMIT 300;"""

ORDER_LIFECYCLE_SQL = """
SELECT status,
       changed_at,
       LEAD(changed_at) OVER (ORDER BY changed_at, history_id) AS next_change,
       ROUND(EXTRACT(EPOCH FROM (LEAD(changed_at) OVER (ORDER BY changed_at, history_id) - changed_at)) / 60.0, 1) AS minutes_in_state
FROM order_status_history
WHERE order_id = %(order_id)s
ORDER BY changed_at, history_id;"""

HEATMAP_SQL = """
SELECT EXTRACT(ISODOW FROM order_time)::int AS weekday,
       EXTRACT(HOUR FROM order_time)::int AS hour,
       COUNT(*) AS orders
FROM orders
GROUP BY 1, 2
ORDER BY 1, 2;"""

DELIVERY_TREND_SQL = """
SELECT DATE_TRUNC('week', o.order_time)::date AS week,
       ROUND(AVG(EXTRACT(EPOCH FROM (d.delivered_time - o.order_time)) / 60)::numeric, 1) AS avg_minutes,
       ROUND((PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (d.delivered_time - o.order_time)) / 60))::numeric, 1) AS p90_minutes,
       COUNT(*) AS deliveries
FROM orders o
JOIN delivery d ON d.order_id = o.order_id
WHERE d.delivered_time IS NOT NULL
GROUP BY 1
ORDER BY 1;"""

STATE_AT_SQL = """
SELECT status, COUNT(*) AS orders
FROM (
    SELECT DISTINCT ON (h.order_id) h.order_id, h.status
    FROM order_status_history h
    WHERE h.changed_at <= %(moment)s
      AND h.changed_at >= %(moment)s::timestamp - INTERVAL '3 hours'
    ORDER BY h.order_id, h.changed_at DESC, h.history_id DESC
) latest
GROUP BY status
ORDER BY orders DESC;"""


def price_history(item_id):
    return database.run_query(PRICE_HISTORY_SQL, {"item_id": int(item_id)})


def menu_as_of(restaurant_id, moment):
    return database.run_query(MENU_AS_OF_SQL, {"restaurant_id": int(restaurant_id), "moment": moment})


def recent_changes():
    frame = database.fetch(RECENT_CHANGES_SQL)
    frame = frame[frame["old_price"].notna()]
    return frame


def order_lifecycle(order_id):
    return database.run_query(ORDER_LIFECYCLE_SQL, {"order_id": int(order_id)})


def weekly_heatmap():
    return database.fetch(HEATMAP_SQL)


def delivery_trend():
    return database.fetch(DELIVERY_TREND_SQL)


def state_at(moment):
    return database.run_query(STATE_AT_SQL, {"moment": moment})


def change_price(item_id, new_price):
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE menu_item SET price = %s WHERE item_id = %s", (float(new_price), int(item_id)))
        connection.commit()
        return True, "Price updated. Trigger trg_price_history closed the old period and opened a new one."
    except Exception as error:
        connection.rollback()
        return False, str(error).splitlines()[0]
    finally:
        connection.close()
