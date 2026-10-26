import random
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2
import streamlit as st

from core import database
from core import generator
from core import orders
from core import tracking

PAYMENT_METHODS = {
    "UPI": "UPI",
    "Credit / Debit card": "CARD",
    "Wallet": "WALLET",
    "Net banking": "NETBANKING",
    "Cash on delivery": "CASH",
}

SCHEDULE = [("ACCEPTED", 8), ("PREPARING", 20), ("PICKED_UP", 60), ("DELIVERED", 120)]

SPEEDS = {
    "Quick (about 1 min)": 0.5,
    "Demo (about 2 min)": 1.0,
    "Realistic (about 12 min)": 6.0,
}

STATUS_TITLE = {
    "PLACED": "Order placed",
    "ACCEPTED": "Restaurant accepted your order",
    "PREPARING": "Your food is being prepared",
    "PICKED_UP": "Your order is on the way",
    "DELIVERED": "Delivered. Enjoy your meal!",
    "CANCELLED": "Order cancelled",
}

STATUS_ICON = {
    "PLACED": "📝",
    "ACCEPTED": "✅",
    "PREPARING": "👩‍🍳",
    "PICKED_UP": "🛵",
    "DELIVERED": "🎉",
    "CANCELLED": "✖️",
}

PREP_MINUTES = {"North Indian": 20, "South Indian": 12, "Chinese": 16, "Italian": 20, "Biryani": 17, "Street Food": 9,
                "Cafe": 12, "Desserts": 8, "Coastal": 20, "Burgers": 12, "Healthy": 12, "Mughlai": 20}

offset_cache = {"value": None, "at": 0}

CREATE_CUSTOMER_SQL = """INSERT INTO customer (customer_id, name, phone, email, address, locality, latitude, longitude, joined_on)
SELECT COALESCE(MAX(customer_id), 0) + 1, %(name)s, %(phone)s, %(email)s, %(address)s, %(locality)s, %(lat)s, %(lon)s, CURRENT_DATE
FROM customer
RETURNING customer_id;"""

RESTAURANTS_SQL = """SELECT r.restaurant_id, r.name, r.cuisine, r.locality, r.address, r.rating, r.cost_for_two, r.is_veg,
       TO_CHAR(r.opens_at, 'HH24:MI') AS opens_at, TO_CHAR(r.closes_at, 'HH24:MI') AS closes_at,
       ROUND(distance_km(%(lat)s, %(lon)s, r.latitude, r.longitude)::numeric, 1) AS distance_km,
       COALESCE(s.total_orders, 0) AS total_orders
FROM restaurant r
LEFT JOIN restaurant_stats s ON s.restaurant_id = r.restaurant_id
WHERE distance_km(%(lat)s, %(lon)s, r.latitude, r.longitude) <= %(radius)s
ORDER BY distance_km;"""

MENU_SQL = """SELECT m.item_id, m.item_name, m.category, m.price, m.stock, m.is_veg,
       COALESCE(p.sold, 0) AS sold
FROM menu_item m
LEFT JOIN (
    SELECT item_id, SUM(quantity) AS sold
    FROM order_item
    GROUP BY item_id
) p ON p.item_id = m.item_id
WHERE m.restaurant_id = %(restaurant_id)s
ORDER BY m.category, m.item_name;"""

ORDERS_SQL = """SELECT o.order_id, o.order_time, o.status, o.total_amount,
       r.restaurant_id, r.name AS restaurant, r.cuisine,
       (SELECT STRING_AGG(m.item_name || ' x ' || oi.quantity, ', ' ORDER BY m.item_name)
        FROM order_item oi
        JOIN menu_item m ON m.item_id = oi.item_id
        WHERE oi.order_id = o.order_id) AS items,
       p.method, p.status AS payment_status,
       rv.stars
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
LEFT JOIN payment p ON p.order_id = o.order_id
LEFT JOIN review rv ON rv.order_id = o.order_id
WHERE o.customer_id = %(customer_id)s
ORDER BY o.order_time DESC
LIMIT 50;"""

TRACK_SQL = """SELECT o.order_id, o.status, o.order_time, o.total_amount, o.customer_id,
       EXTRACT(EPOCH FROM (NOW()::timestamp - o.order_time)) AS elapsed,
       r.restaurant_id, r.name AS restaurant, r.cuisine, r.address AS restaurant_address,
       r.latitude AS r_lat, r.longitude AS r_lon,
       c.name AS customer, c.address AS customer_address, c.latitude AS c_lat, c.longitude AS c_lon,
       p.method, p.status AS payment_status,
       d.distance_km, dp.name AS partner_name, dp.vehicle, dp.rating AS partner_rating, dp.phone AS partner_phone
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
JOIN customer c ON c.customer_id = o.customer_id
LEFT JOIN payment p ON p.order_id = o.order_id
LEFT JOIN delivery d ON d.order_id = o.order_id
LEFT JOIN delivery_partner dp ON dp.partner_id = d.partner_id
WHERE o.order_id = %(order_id)s;"""


def clock_offset():
    now = time.time()
    if offset_cache["value"] is None or now - offset_cache["at"] > 600:
        database_now = database.fetch_value("SELECT NOW()::timestamp")
        real_now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
        half_hours = round((real_now - database_now).total_seconds() / 1800)
        offset_cache["value"] = timedelta(minutes=half_hours * 30)
        offset_cache["at"] = now
    return offset_cache["value"]


def local_time(value):
    return value + clock_offset()


def clock_text(value):
    moment = local_time(value)
    today = (datetime.now(ZoneInfo("Asia/Kolkata"))).date()
    prefix = moment.strftime("%d %b")
    if moment.date() == today:
        prefix = "Today"
    elif moment.date() == today - timedelta(days=1):
        prefix = "Yesterday"
    return prefix + ", " + moment.strftime("%I:%M %p").lstrip("0")


def rupees(value):
    value = float(value)
    if value == int(value):
        return "₹" + format(int(value), ",")
    return "₹" + format(value, ",.2f")


def bill(subtotal):
    subtotal = float(subtotal)
    delivery_fee = 0
    if subtotal < 199:
        delivery_fee = 30
    taxes = round(subtotal * 0.05, 2)
    total = round(subtotal + delivery_fee + subtotal * 0.05, 2)
    return {"subtotal": subtotal, "delivery_fee": delivery_fee, "taxes": taxes, "total": total}


def locality_names():
    names = []
    for locality in generator.LOCALITIES:
        names.append(locality[0])
    return names


def locality_centre(name):
    for locality in generator.LOCALITIES:
        if locality[0] == name:
            return locality[1], locality[2]
    return generator.LOCALITIES[0][1], generator.LOCALITIES[0][2]


def customer_options():
    frame = database.fetch("SELECT customer_id, name, locality, phone FROM customer ORDER BY name, customer_id")
    labels = {}
    for row in frame.to_dict("records"):
        labels[row["name"] + " · " + row["locality"] + " · " + row["phone"]] = int(row["customer_id"])
    return labels


def get_customer(customer_id):
    frame = database.fetch("""SELECT customer_id, name, phone, email, address, locality, latitude, longitude, joined_on
                              FROM customer WHERE customer_id = %s""", (int(customer_id),))
    if len(frame) == 0:
        return None
    row = frame.iloc[0].to_dict()
    row["customer_id"] = int(row["customer_id"])
    row["latitude"] = float(row["latitude"])
    row["longitude"] = float(row["longitude"])
    return row


def create_customer(name, phone, email, address, locality):
    name = name.strip()
    phone = re.sub(r"\D", "", phone)
    email = email.strip().lower()
    address = address.strip()
    if len(name) < 2:
        return False, "Please enter your full name.", ""
    if len(phone) != 10:
        return False, "Phone number must have 10 digits.", ""
    if not re.match(r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$", email):
        return False, "Please enter a valid email address.", ""
    if len(address) < 5:
        return False, "Please enter your delivery address.", ""
    centre_lat, centre_lon = locality_centre(locality)
    params = {"name": name, "phone": phone, "email": email, "address": address + ", " + locality + ", Mumbai", "locality": locality,
              "lat": round(centre_lat + random.uniform(-0.006, 0.006), 6), "lon": round(centre_lon + random.uniform(-0.006, 0.006), 6)}
    shown_sql = database.render(CREATE_CUSTOMER_SQL, params)
    for attempt in range(3):
        connection = database.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(CREATE_CUSTOMER_SQL, params)
            customer_id = cursor.fetchone()[0]
            return True, customer_id, shown_sql
        except psycopg2.errors.UniqueViolation as error:
            constraint = str(error.diag.constraint_name)
            if "phone" in constraint:
                return False, "This phone number already has an account. Use 'I already have an account' instead.", shown_sql
            if "email" in constraint:
                return False, "This email is already registered. Use 'I already have an account' instead.", shown_sql
        except Exception as error:
            return False, str(error).splitlines()[0], shown_sql
        finally:
            connection.close()
    return False, "Could not create the account right now, please try again.", shown_sql


def update_address(customer_id, address, locality, keep_position):
    customer = get_customer(customer_id)
    lat = customer["latitude"]
    lon = customer["longitude"]
    if not keep_position:
        centre_lat, centre_lon = locality_centre(locality)
        lat = round(centre_lat + random.uniform(-0.006, 0.006), 6)
        lon = round(centre_lon + random.uniform(-0.006, 0.006), 6)
    sql = "UPDATE customer SET address = %(address)s, locality = %(locality)s, latitude = %(lat)s, longitude = %(lon)s WHERE customer_id = %(customer_id)s;"
    params = {"address": address.strip(), "locality": locality, "lat": lat, "lon": lon, "customer_id": int(customer_id)}
    try:
        database.execute(sql, params)
    except Exception as error:
        return False, str(error).splitlines()[0], ""
    return True, "Address updated", database.render(sql, params)


def restaurants_near(lat, lon, radius):
    params = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "radius": float(radius)}
    frame, elapsed = database.run_query(RESTAURANTS_SQL, params)
    prep = []
    for row in frame.to_dict("records"):
        prep.append(int(PREP_MINUTES.get(row["cuisine"], 15) + float(row["distance_km"]) * 4 + 5))
    frame["eta_minutes"] = prep
    return frame, database.render(RESTAURANTS_SQL, params), elapsed


def restaurant_info(restaurant_id, lat, lon):
    frame = database.fetch("""SELECT restaurant_id, name, cuisine, locality, address, rating, cost_for_two, is_veg,
                                     TO_CHAR(opens_at, 'HH24:MI') AS opens_at, TO_CHAR(closes_at, 'HH24:MI') AS closes_at,
                                     ROUND(distance_km(%s, %s, latitude, longitude)::numeric, 1) AS distance_km
                              FROM restaurant WHERE restaurant_id = %s""", (float(lat), float(lon), int(restaurant_id)))
    if len(frame) == 0:
        return None
    row = frame.iloc[0].to_dict()
    row["restaurant_id"] = int(row["restaurant_id"])
    row["eta_minutes"] = int(PREP_MINUTES.get(row["cuisine"], 15) + float(row["distance_km"]) * 4 + 5)
    return row


def menu_for(restaurant_id):
    params = {"restaurant_id": int(restaurant_id)}
    frame, elapsed = database.run_query(MENU_SQL, params)
    return frame, database.render(MENU_SQL, params), elapsed


def cart_lines(item_ids):
    if not item_ids:
        return []
    frame = database.fetch("SELECT item_id, item_name, price, stock, is_veg FROM menu_item WHERE item_id = ANY(%s) ORDER BY item_name", (list(item_ids),))
    return frame.to_dict("records")


def active_order(customer_id):
    frame = database.fetch("""SELECT o.order_id, o.status, r.name AS restaurant
                              FROM orders o JOIN restaurant r ON r.restaurant_id = o.restaurant_id
                              WHERE o.customer_id = %s AND o.status NOT IN ('DELIVERED', 'CANCELLED')
                                AND o.order_time > NOW()::timestamp - INTERVAL '6 hours'
                              ORDER BY o.order_time DESC LIMIT 1""", (int(customer_id),))
    if len(frame) == 0:
        return None
    return frame.iloc[0].to_dict()


def my_orders(customer_id):
    params = {"customer_id": int(customer_id)}
    frame, elapsed = database.run_query(ORDERS_SQL, params)
    return frame, database.render(ORDERS_SQL, params)


def order_lines(order_id):
    return database.fetch("""SELECT m.item_name, oi.quantity, oi.unit_price, oi.quantity * oi.unit_price AS line_total
                             FROM order_item oi JOIN menu_item m ON m.item_id = oi.item_id
                             WHERE oi.order_id = %s ORDER BY m.item_name""", (int(order_id),))


def order_history(order_id):
    return database.fetch("SELECT status, changed_at FROM order_status_history WHERE order_id = %s ORDER BY changed_at, history_id", (int(order_id),))


def track_info(order_id):
    params = {"order_id": int(order_id)}
    frame = database.fetch(TRACK_SQL, params)
    if len(frame) == 0:
        return None
    row = frame.iloc[0].to_dict()
    for key in ["r_lat", "r_lon", "c_lat", "c_lon", "elapsed"]:
        row[key] = float(row[key])
    return row


def reorder(order_id):
    lines = database.fetch("""SELECT oi.item_id, oi.quantity, m.stock, m.restaurant_id
                              FROM order_item oi JOIN menu_item m ON m.item_id = oi.item_id WHERE oi.order_id = %s""", (int(order_id),))
    items = {}
    restaurant_id = None
    for row in lines.to_dict("records"):
        restaurant_id = int(row["restaurant_id"])
        quantity = min(int(row["quantity"]), int(row["stock"]), 10)
        if quantity > 0:
            items[int(row["item_id"])] = quantity
    return restaurant_id, items


def add_review(order_id, customer_id, restaurant_id, stars, comment):
    sql = """INSERT INTO review (order_id, customer_id, restaurant_id, stars, comment, reviewed_at)
VALUES (%(order_id)s, %(customer_id)s, %(restaurant_id)s, %(stars)s, %(comment)s, NOW())
RETURNING review_id;"""
    params = {"order_id": int(order_id), "customer_id": int(customer_id), "restaurant_id": int(restaurant_id),
              "stars": int(stars), "comment": comment.strip() or None}
    try:
        database.execute(sql, params)
    except psycopg2.errors.UniqueViolation:
        return False, "You have already reviewed this order.", ""
    except Exception as error:
        return False, str(error).splitlines()[0], ""
    return True, "Thanks for your feedback!", database.render(sql, params)


def check_payment(method, details):
    if details.get("force_fail"):
        return "declined", "Payment declined by the bank (test mode)."
    if method == "CASH":
        return "ok", "Pay in cash when your order arrives."
    if method == "UPI":
        upi = details.get("upi", "").strip()
        if not re.match(r"^[\w.\-]{2,}@[a-zA-Z]{2,}$", upi):
            return "invalid", "Enter a valid UPI ID, for example name@okbank."
        if upi.lower().endswith("@fail"):
            return "declined", "The UPI request was declined."
        return "ok", "UPI payment approved."
    if method == "CARD":
        digits = re.sub(r"\D", "", details.get("card", ""))
        if len(digits) != 16:
            return "invalid", "Card number must have 16 digits."
        if not re.match(r"^(0[1-9]|1[0-2])/\d{2}$", details.get("expiry", "").strip()):
            return "invalid", "Enter the expiry as MM/YY."
        if not re.match(r"^\d{3}$", details.get("cvv", "").strip()):
            return "invalid", "CVV must have 3 digits."
        if digits.endswith("0002"):
            return "declined", "Your card was declined by the bank."
        return "ok", "Card payment approved."
    if method == "WALLET":
        return "ok", "Wallet payment approved."
    if method == "NETBANKING":
        return "ok", "Net banking payment approved."
    return "invalid", "Choose a payment method."


def release_idle_partners():
    database.execute("""UPDATE delivery_partner dp SET is_available = TRUE
                        WHERE is_available = FALSE
                          AND NOT EXISTS (
                              SELECT 1 FROM delivery d JOIN orders o ON o.order_id = d.order_id
                              WHERE d.partner_id = dp.partner_id AND o.status IN ('PREPARING', 'PICKED_UP')
                                AND o.order_time > NOW()::timestamp - INTERVAL '3 hours')""")


def target_status(elapsed, speed):
    reached = "PLACED"
    for status, seconds in SCHEDULE:
        if elapsed >= seconds * speed:
            reached = status
    return reached


def progress_order(order_id, speed):
    moves = 0
    flow = tracking.STATUS_FLOW
    while moves < 5:
        info = track_info(order_id)
        if info is None or info["status"] in ["DELIVERED", "CANCELLED"]:
            break
        target = target_status(info["elapsed"], speed)
        if flow.index(info["status"]) >= flow.index(target):
            break
        if target in ["PREPARING", "PICKED_UP"] or info["status"] == "ACCEPTED":
            release_idle_partners()
        new_status, log = orders.advance_order(order_id)
        if new_status is None:
            break
        moves += 1
    return moves


def route_points(info):
    return tracking.make_route(info["r_lat"], info["r_lon"], info["c_lat"], info["c_lon"], int(info["order_id"]))


def point_along(route, fraction):
    fraction = max(0.0, min(1.0, fraction))
    lengths = []
    total = 0
    for i in range(len(route) - 1):
        length = ((route[i + 1][0] - route[i][0]) ** 2 + (route[i + 1][1] - route[i][1]) ** 2) ** 0.5
        lengths.append(length)
        total = total + length
    target = total * fraction
    walked = 0
    for i in range(len(lengths)):
        if walked + lengths[i] >= target and lengths[i] > 0:
            share = (target - walked) / lengths[i]
            lon = route[i][0] + (route[i + 1][0] - route[i][0]) * share
            lat = route[i][1] + (route[i + 1][1] - route[i][1]) * share
            return lon, lat
        walked = walked + lengths[i]
    return route[-1][0], route[-1][1]


def rider_position(info, route, speed):
    status = info["status"]
    if status == "DELIVERED":
        return point_along(route, 1.0)
    if status == "PICKED_UP":
        start = 60 * speed
        end = 120 * speed
        return point_along(route, (info["elapsed"] - start) / (end - start))
    return point_along(route, 0.0)


def eta_text(info, speed):
    if info["status"] == "DELIVERED":
        return "Delivered"
    if info["status"] == "CANCELLED":
        return "Cancelled"
    remaining = int(120 * speed - info["elapsed"])
    if remaining <= 0:
        return "Arriving now"
    minutes = remaining // 60
    seconds = remaining % 60
    if minutes > 0:
        return str(minutes) + " min " + str(seconds).zfill(2) + " sec"
    return str(seconds) + " sec"
