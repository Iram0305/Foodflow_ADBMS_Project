import time

import psycopg2

from core import database
from core import spatial
from core import tracking

FAILURE_MODES = [
    "No failure (happy path)",
    "Payment gateway declines the card",
    "Constraint violation inside the transaction",
    "Server crash before COMMIT",
]


class PaymentDeclined(Exception):
    pass


class SimulatedCrash(Exception):
    pass


class Recorder:
    def __init__(self, cursor):
        self.cursor = cursor
        self.steps = []
        self.start = time.perf_counter()

    def run(self, label, sql, params=None, show=None):
        moment = (time.perf_counter() - self.start) * 1000
        try:
            self.cursor.execute(sql, params)
        except Exception as error:
            self.steps.append({"label": label, "sql": show or sql.strip(), "ok": False,
                               "detail": str(error).splitlines()[0], "ms": round(moment, 1)})
            raise
        detail = ""
        if self.cursor.description is not None:
            rows = self.cursor.fetchall()
            detail = []
            for row in rows:
                clean = []
                for value in row:
                    if type(value).__name__ == "Decimal":
                        value = float(value)
                    clean.append(value)
                detail.append(tuple(clean))
        elif self.cursor.rowcount < 0:
            detail = "OK"
        else:
            detail = str(self.cursor.rowcount) + " row(s) affected"
        self.steps.append({"label": label, "sql": show or sql.strip(), "ok": True, "detail": detail, "ms": round(moment, 1)})
        return detail

    def note(self, label, detail, ok=True):
        moment = (time.perf_counter() - self.start) * 1000
        self.steps.append({"label": label, "sql": "", "ok": ok, "detail": detail, "ms": round(moment, 1)})


def stock_snapshot(item_ids):
    if not item_ids:
        return {}
    frame = database.fetch("SELECT item_id, stock FROM menu_item WHERE item_id = ANY(%s)", (list(item_ids),))
    snapshot = {}
    for row in frame.to_dict("records"):
        snapshot[int(row["item_id"])] = int(row["stock"])
    return snapshot


def place_order(customer_id, restaurant_id, cart, method, failure_mode):
    item_ids = list(cart.keys())
    before = stock_snapshot(item_ids)
    connection = database.connect(autocommit=True)
    cursor = connection.cursor()
    recorder = Recorder(cursor)
    order_id = None
    outcome = "COMMITTED"
    reason = ""
    try:
        recorder.run("Start transaction", "BEGIN ISOLATION LEVEL READ COMMITTED;")
        total = 0
        lines = []
        for item_id in item_ids:
            quantity = int(cart[item_id])
            rows = recorder.run("Lock the menu row and check stock",
                                "SELECT item_name, price, stock FROM menu_item WHERE item_id = %s AND restaurant_id = %s FOR UPDATE;",
                                (int(item_id), int(restaurant_id)),
                                "SELECT item_name, price, stock FROM menu_item\nWHERE item_id = " + str(item_id) + " AND restaurant_id = " + str(restaurant_id) + "\nFOR UPDATE;")
            if not rows:
                raise ValueError("Item " + str(item_id) + " does not belong to this restaurant")
            name, price, stock = rows[0]
            if stock < quantity:
                recorder.note("Stock check failed", name + " has only " + str(stock) + " left but " + str(quantity) + " requested", ok=False)
                raise ValueError("Not enough stock for " + name)
            recorder.run("Reduce inventory",
                         "UPDATE menu_item SET stock = stock - %s, version = version + 1 WHERE item_id = %s AND stock >= %s;",
                         (quantity, int(item_id), quantity),
                         "UPDATE menu_item SET stock = stock - " + str(quantity) + ", version = version + 1\nWHERE item_id = " + str(item_id) + " AND stock >= " + str(quantity) + ";")
            total = total + float(price) * quantity
            lines.append((int(item_id), quantity, float(price)))

        delivery_fee = 0
        if total < 199:
            delivery_fee = 30
        grand_total = round(total + delivery_fee + total * 0.05, 2)

        rows = recorder.run("Create the order",
                            "INSERT INTO orders (customer_id, restaurant_id, order_time, status, total_amount) VALUES (%s, %s, NOW(), 'PLACED', %s) RETURNING order_id;",
                            (int(customer_id), int(restaurant_id), grand_total),
                            "INSERT INTO orders (customer_id, restaurant_id, order_time, status, total_amount)\nVALUES (" + str(customer_id) + ", " + str(restaurant_id) + ", NOW(), 'PLACED', " + str(grand_total) + ")\nRETURNING order_id;")
        order_id = rows[0][0]

        for item_id, quantity, price in lines:
            recorder.run("Add order item",
                         "INSERT INTO order_item (order_id, item_id, quantity, unit_price) VALUES (%s, %s, %s, %s);",
                         (order_id, item_id, quantity, price),
                         "INSERT INTO order_item VALUES (" + str(order_id) + ", " + str(item_id) + ", " + str(quantity) + ", " + str(price) + ");")

        recorder.run("Write status history",
                     "INSERT INTO order_status_history (order_id, status, changed_at) VALUES (%s, 'PLACED', NOW());",
                     (order_id,),
                     "INSERT INTO order_status_history (order_id, status, changed_at)\nVALUES (" + str(order_id) + ", 'PLACED', NOW());")

        if failure_mode == FAILURE_MODES[2]:
            recorder.run("Insert a payment with a negative amount",
                         "INSERT INTO payment (order_id, amount, method, status, paid_at) VALUES (%s, %s, %s, 'SUCCESS', NOW());",
                         (order_id, -1 * grand_total, method),
                         "INSERT INTO payment (order_id, amount, method, status, paid_at)\nVALUES (" + str(order_id) + ", " + str(-1 * grand_total) + ", '" + method + "', 'SUCCESS', NOW());")

        recorder.note("Call payment gateway", "Charging Rs " + str(grand_total) + " via " + method)
        time.sleep(0.4)
        if failure_mode == FAILURE_MODES[1]:
            recorder.note("Payment gateway response", "DECLINED: insufficient funds", ok=False)
            raise PaymentDeclined("Payment declined by gateway")

        payment_status = "SUCCESS"
        if method == "CASH":
            payment_status = "PENDING"
        recorder.run("Record the payment",
                     "INSERT INTO payment (order_id, amount, method, status, paid_at) VALUES (%s, %s, %s, %s, NOW());",
                     (order_id, grand_total, method, payment_status),
                     "INSERT INTO payment (order_id, amount, method, status, paid_at)\nVALUES (" + str(order_id) + ", " + str(grand_total) + ", '" + method + "', '" + payment_status + "', NOW());")

        if failure_mode == FAILURE_MODES[3]:
            recorder.note("Connection lost", "The app server died before sending COMMIT", ok=False)
            connection.close()
            raise SimulatedCrash("Connection closed before COMMIT")

        recorder.run("Make it permanent", "COMMIT;")
    except Exception as error:
        outcome = "ROLLED BACK"
        reason = str(error).splitlines()[0]
        if not connection.closed:
            try:
                recorder.run("Undo everything", "ROLLBACK;")
            except Exception:
                pass
        else:
            recorder.note("Automatic rollback", "PostgreSQL discards any transaction whose connection ends without COMMIT")
    finally:
        if not connection.closed:
            connection.close()

    after = stock_snapshot(item_ids)
    order_exists = False
    if order_id is not None:
        order_exists = bool(database.fetch_value("SELECT EXISTS (SELECT 1 FROM orders WHERE order_id = %s)", (order_id,)))
    if outcome == "COMMITTED":
        try:
            tracking.refresh_order(order_id)
        except Exception:
            pass
    return {"outcome": outcome, "reason": reason, "order_id": order_id, "order_exists": order_exists,
            "steps": recorder.steps, "before": before, "after": after}


def next_status(current):
    flow = tracking.STATUS_FLOW
    if current not in flow:
        return None
    position = flow.index(current)
    if position + 1 >= len(flow):
        return None
    return flow[position + 1]


def advance_order(order_id):
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    log = []
    try:
        cursor.execute("SELECT o.status, r.latitude, r.longitude, c.latitude, c.longitude FROM orders o JOIN restaurant r ON r.restaurant_id = o.restaurant_id JOIN customer c ON c.customer_id = o.customer_id WHERE o.order_id = %s FOR UPDATE OF o", (int(order_id),))
        row = cursor.fetchone()
        if row is None:
            connection.rollback()
            return None, ["Order not found"]
        current, r_lat, r_lon, c_lat, c_lon = row
        new_status = next_status(current)
        if new_status is None:
            connection.rollback()
            return None, ["Order is already " + current]

        cursor.execute("UPDATE orders SET status = %s WHERE order_id = %s", (new_status, int(order_id)))
        log.append("UPDATE orders SET status = '" + new_status + "'  (trigger trg_status_history writes the history row)")

        if new_status == "PREPARING":
            cursor.execute("SELECT 1 FROM delivery WHERE order_id = %s", (int(order_id),))
            if cursor.fetchone() is None:
                partners, sql, elapsed = spatial.nearest_partners(r_lat, r_lon, 1)
                if len(partners) > 0:
                    partner = partners.iloc[0]
                    cursor.execute("SELECT distance_km(%s, %s, %s, %s)", (float(r_lat), float(r_lon), float(c_lat), float(c_lon)))
                    straight_km = cursor.fetchone()[0]
                    road_km = round(straight_km * 1.3 + 0.3, 2)
                    cursor.execute("INSERT INTO delivery (order_id, partner_id, distance_km) VALUES (%s, %s, %s)", (int(order_id), int(partner["partner_id"]), road_km))
                    cursor.execute("UPDATE delivery_partner SET is_available = FALSE WHERE partner_id = %s", (int(partner["partner_id"]),))
                    log.append("Spatial query picked nearest free partner: " + str(partner["name"]) + " (" + str(partner["distance_km"]) + " km away)")
        if new_status == "PICKED_UP":
            cursor.execute("UPDATE delivery SET pickup_time = NOW() WHERE order_id = %s", (int(order_id),))
            log.append("UPDATE delivery SET pickup_time = NOW()")
        if new_status == "DELIVERED":
            cursor.execute("UPDATE delivery SET delivered_time = NOW() WHERE order_id = %s RETURNING partner_id", (int(order_id),))
            done = cursor.fetchone()
            if done is not None:
                cursor.execute("UPDATE delivery_partner SET is_available = TRUE WHERE partner_id = %s", (done[0],))
            cursor.execute("UPDATE payment SET status = 'SUCCESS' WHERE order_id = %s AND status = 'PENDING'", (int(order_id),))
            log.append("Delivery closed, partner released, cash payment settled")
        connection.commit()
    except Exception as error:
        connection.rollback()
        connection.close()
        return None, ["Failed: " + str(error).splitlines()[0]]
    connection.close()
    tracking.refresh_order(order_id)
    log.append("MongoDB tracking document re-synced from PostgreSQL")
    return new_status, log


def cancel_order(order_id):
    connection = database.connect(autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT status FROM orders WHERE order_id = %s FOR UPDATE", (int(order_id),))
        row = cursor.fetchone()
        if row is None or row[0] in ["DELIVERED", "CANCELLED", "PICKED_UP"]:
            connection.rollback()
            return False, "Order cannot be cancelled now"
        cursor.execute("UPDATE menu_item m SET stock = m.stock + oi.quantity FROM order_item oi WHERE oi.order_id = %s AND oi.item_id = m.item_id", (int(order_id),))
        restored = cursor.rowcount
        cursor.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = %s", (int(order_id),))
        cursor.execute("UPDATE payment SET status = CASE WHEN status = 'PENDING' THEN 'FAILED' ELSE 'REFUNDED' END WHERE order_id = %s", (int(order_id),))
        cursor.execute("UPDATE delivery_partner SET is_available = TRUE WHERE partner_id IN (SELECT partner_id FROM delivery WHERE order_id = %s)", (int(order_id),))
        connection.commit()
    except Exception as error:
        connection.rollback()
        connection.close()
        return False, str(error).splitlines()[0]
    connection.close()
    tracking.refresh_order(order_id)
    return True, "Cancelled in one transaction: stock restored for " + str(restored) + " item(s), payment refunded"
