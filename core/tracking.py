import random

from core import config
from core import database

STATUS_FLOW = ["PLACED", "ACCEPTED", "PREPARING", "PICKED_UP", "DELIVERED"]

ACTOR_FOR_STATUS = {
    "PLACED": "customer",
    "ACCEPTED": "restaurant",
    "PREPARING": "restaurant",
    "PICKED_UP": "delivery_partner",
    "DELIVERED": "delivery_partner",
    "CANCELLED": "system",
}

NOTE_FOR_STATUS = {
    "PLACED": "Order placed from the app",
    "ACCEPTED": "Restaurant accepted the order",
    "PREPARING": "Kitchen started preparing",
    "PICKED_UP": "Partner picked up the order",
    "DELIVERED": "Order handed over to customer",
    "CANCELLED": "Order cancelled",
}

store = {"collection": None, "mode": None, "error": ""}


def get_store():
    if store["collection"] is not None:
        return store["collection"], store["mode"], store["error"]
    try:
        from pymongo import MongoClient
        client = MongoClient(config.mongo_url(), serverSelectionTimeoutMS=2500)
        client.admin.command("ping")
        store["collection"] = client[config.mongo_database()]["order_tracking"]
        store["mode"] = "MongoDB"
    except Exception as error:
        import mongomock
        client = mongomock.MongoClient()
        store["collection"] = client[config.mongo_database()]["order_tracking"]
        store["mode"] = "In-memory MongoDB (mongomock)"
        store["error"] = str(error).splitlines()[0][:160]
    return store["collection"], store["mode"], store["error"]


def make_route(start_lat, start_lon, end_lat, end_lon, seed):
    rng = random.Random(seed)
    points = []
    steps = 8
    for i in range(steps + 1):
        share = i / steps
        lat = start_lat + (end_lat - start_lat) * share
        lon = start_lon + (end_lon - start_lon) * share
        if 0 < i < steps:
            lat = lat + rng.uniform(-0.0025, 0.0025)
            lon = lon + rng.uniform(-0.0025, 0.0025)
        points.append([round(lon, 6), round(lat, 6)])
    return points


def plain_time(value):
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    return value


def build_document(order, events, delivery):
    doc = {
        "order_id": int(order["order_id"]),
        "customer": {"id": int(order["customer_id"]), "name": order["customer_name"], "locality": order["customer_locality"]},
        "restaurant": {"id": int(order["restaurant_id"]), "name": order["restaurant_name"], "cuisine": order["cuisine"]},
        "current_status": order["status"],
        "placed_at": plain_time(order["order_time"]),
        "total_amount": float(order["total_amount"]),
        "payment_method": order["method"],
        "events": [],
    }
    route = None
    if delivery is not None:
        route = make_route(float(order["r_lat"]), float(order["r_lon"]), float(order["c_lat"]), float(order["c_lon"]), int(order["order_id"]))
        doc["partner"] = {"id": int(delivery["partner_id"]), "name": delivery["partner_name"], "vehicle": delivery["vehicle"]}
        doc["route"] = {"type": "LineString", "coordinates": route}
        doc["distance_km"] = float(delivery["distance_km"])
    for event in events:
        entry = {"status": event["status"], "time": plain_time(event["changed_at"]), "actor": ACTOR_FOR_STATUS.get(event["status"], "system"),
                 "note": NOTE_FOR_STATUS.get(event["status"], "")}
        if event["status"] in ["ACCEPTED", "PREPARING"]:
            entry["location"] = {"type": "Point", "coordinates": [float(order["r_lon"]), float(order["r_lat"])]}
        if event["status"] == "PICKED_UP" and route is not None:
            entry["location"] = {"type": "Point", "coordinates": route[0]}
        if event["status"] == "DELIVERED" and route is not None:
            entry["location"] = {"type": "Point", "coordinates": route[-1]}
        if event["status"] == "CANCELLED":
            if order["payment_status"] == "FAILED":
                entry["reason"] = "Payment failed"
            else:
                entry["reason"] = random.Random(int(order["order_id"])).choice(["Restaurant too busy", "Item out of stock", "Customer request"])
        doc["events"].append(entry)
    return doc


def load_orders(order_ids=None):
    sql = """
        SELECT o.order_id, o.customer_id, o.restaurant_id, o.status, o.order_time, o.total_amount,
               c.name AS customer_name, c.locality AS customer_locality, c.latitude AS c_lat, c.longitude AS c_lon,
               r.name AS restaurant_name, r.cuisine, r.latitude AS r_lat, r.longitude AS r_lon,
               p.method, p.status AS payment_status
        FROM orders o
        JOIN customer c ON c.customer_id = o.customer_id
        JOIN restaurant r ON r.restaurant_id = o.restaurant_id
        LEFT JOIN payment p ON p.order_id = o.order_id
    """
    params = None
    if order_ids is not None:
        sql = sql + " WHERE o.order_id = ANY(%s)"
        params = (order_ids,)
    orders = database.fetch(sql, params)

    history_sql = "SELECT order_id, status, changed_at FROM order_status_history"
    delivery_sql = """
        SELECT d.order_id, d.partner_id, d.distance_km, dp.name AS partner_name, dp.vehicle
        FROM delivery d JOIN delivery_partner dp ON dp.partner_id = d.partner_id
    """
    if order_ids is not None:
        history_sql = history_sql + " WHERE order_id = ANY(%s)"
        delivery_sql = delivery_sql + " WHERE d.order_id = ANY(%s)"
    history_sql = history_sql + " ORDER BY order_id, changed_at, history_id"
    history = database.fetch(history_sql, params)
    deliveries = database.fetch(delivery_sql, params)

    events_by_order = {}
    for row in history.to_dict("records"):
        events_by_order.setdefault(row["order_id"], []).append(row)
    delivery_by_order = {}
    for row in deliveries.to_dict("records"):
        delivery_by_order[row["order_id"]] = row

    documents = []
    for order in orders.to_dict("records"):
        events = events_by_order.get(order["order_id"], [])
        delivery = delivery_by_order.get(order["order_id"])
        documents.append(build_document(order, events, delivery))
    return documents


def sync_from_postgres():
    collection, mode, error = get_store()
    collection.delete_many({})
    documents = load_orders()
    batch = []
    for doc in documents:
        batch.append(doc)
        if len(batch) == 2000:
            collection.insert_many(batch)
            batch = []
    if batch:
        collection.insert_many(batch)
    collection.create_index("order_id", unique=True)
    collection.create_index("current_status")
    collection.create_index("placed_at")
    return len(documents)


def ensure_synced():
    collection, mode, error = get_store()
    if collection.count_documents({}) == 0:
        sync_from_postgres()


def refresh_order(order_id):
    collection, mode, error = get_store()
    documents = load_orders([int(order_id)])
    if documents:
        collection.replace_one({"order_id": int(order_id)}, documents[0], upsert=True)
        return documents[0]
    return None


def get_document(order_id):
    collection, mode, error = get_store()
    doc = collection.find_one({"order_id": int(order_id)}, {"_id": 0})
    return doc


def push_event(order_id, status, moment, extra=None):
    collection, mode, error = get_store()
    event = {"status": status, "time": moment, "actor": ACTOR_FOR_STATUS.get(status, "system"), "note": NOTE_FOR_STATUS.get(status, "")}
    if extra:
        for key in extra:
            event[key] = extra[key]
    collection.update_one({"order_id": int(order_id)}, {"$push": {"events": event}, "$set": {"current_status": status}})


def active_orders(limit=40):
    collection, mode, error = get_store()
    cursor = collection.find({"current_status": {"$nin": ["DELIVERED", "CANCELLED"]}},
                             {"_id": 0, "order_id": 1, "current_status": 1, "restaurant.name": 1, "customer.name": 1, "placed_at": 1})
    cursor = cursor.sort("placed_at", -1).limit(limit)
    return list(cursor)


def recent_orders(limit=40):
    collection, mode, error = get_store()
    cursor = collection.find({}, {"_id": 0, "order_id": 1, "current_status": 1, "restaurant.name": 1, "customer.name": 1, "placed_at": 1})
    cursor = cursor.sort("placed_at", -1).limit(limit)
    return list(cursor)


def stage_of(status):
    return {"$arrayElemAt": [{"$filter": {"input": "$events", "as": "e", "cond": {"$eq": ["$$e.status", status]}}}, 0]}


def minutes_between(first, second):
    return {"$divide": [{"$subtract": ["$" + second + ".time", "$" + first + ".time"]}, 60000]}


PIPELINES = {
    "Average minutes spent in each stage": [
        {"$match": {"current_status": "DELIVERED"}},
        {"$project": {"cuisine": "$restaurant.cuisine",
                      "placed": stage_of("PLACED"), "accepted": stage_of("ACCEPTED"), "preparing": stage_of("PREPARING"),
                      "picked": stage_of("PICKED_UP"), "delivered": stage_of("DELIVERED")}},
        {"$project": {"cuisine": 1,
                      "to_accept": minutes_between("placed", "accepted"),
                      "to_start_cooking": minutes_between("accepted", "preparing"),
                      "cooking": minutes_between("preparing", "picked"),
                      "on_the_road": minutes_between("picked", "delivered"),
                      "total": minutes_between("placed", "delivered")}},
        {"$group": {"_id": "$cuisine", "orders": {"$sum": 1},
                    "to_accept": {"$avg": "$to_accept"}, "to_start_cooking": {"$avg": "$to_start_cooking"},
                    "cooking": {"$avg": "$cooking"}, "on_the_road": {"$avg": "$on_the_road"}, "total": {"$avg": "$total"}}},
        {"$sort": {"total": 1}},
    ],
    "Order count by current status": [
        {"$group": {"_id": "$current_status", "orders": {"$sum": 1}, "value": {"$sum": "$total_amount"}}},
        {"$sort": {"orders": -1}},
    ],
    "Tracking events by hour of day": [
        {"$unwind": "$events"},
        {"$group": {"_id": {"$hour": "$events.time"}, "events": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ],
    "Why orders get cancelled": [
        {"$match": {"current_status": "CANCELLED"}},
        {"$unwind": "$events"},
        {"$match": {"events.status": "CANCELLED"}},
        {"$group": {"_id": "$events.reason", "orders": {"$sum": 1}}},
        {"$sort": {"orders": -1}},
    ],
    "Busiest delivery partners": [
        {"$match": {"partner": {"$exists": True}, "current_status": "DELIVERED"}},
        {"$group": {"_id": "$partner.name", "deliveries": {"$sum": 1}, "km": {"$sum": "$distance_km"}}},
        {"$sort": {"deliveries": -1}},
        {"$limit": 10},
    ],
}


def run_pipeline(name):
    collection, mode, error = get_store()
    pipeline = PIPELINES[name]
    return list(collection.aggregate(pipeline))


def document_stats():
    collection, mode, error = get_store()
    total = collection.count_documents({})
    with_route = collection.count_documents({"route": {"$exists": True}})
    live = collection.count_documents({"current_status": {"$nin": ["DELIVERED", "CANCELLED"]}})
    return {"documents": total, "with_route": with_route, "live": live}
