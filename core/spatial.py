from core import database


def engine():
    if database.has_postgis():
        return "PostGIS"
    return "Haversine"


def restaurants_within_sql(use_postgis, cuisine):
    if use_postgis:
        sql = """
SELECT restaurant_id, name, cuisine, locality, rating, cost_for_two, latitude, longitude,
       ROUND((ST_Distance(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) / 1000)::numeric, 2) AS distance_km
FROM restaurant
WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius)s * 1000)"""
    else:
        sql = """
SELECT restaurant_id, name, cuisine, locality, rating, cost_for_two, latitude, longitude,
       ROUND(distance_km(%(lat)s, %(lon)s, latitude, longitude)::numeric, 2) AS distance_km
FROM restaurant
WHERE latitude  BETWEEN %(lat)s - %(radius)s / 111.0 AND %(lat)s + %(radius)s / 111.0
  AND longitude BETWEEN %(lon)s - %(radius)s / 105.0 AND %(lon)s + %(radius)s / 105.0
  AND distance_km(%(lat)s, %(lon)s, latitude, longitude) <= %(radius)s"""
    if cuisine:
        sql = sql + "\n  AND cuisine = %(cuisine)s"
    sql = sql + "\nORDER BY distance_km;"
    return sql


def restaurants_within(lat, lon, radius_km, cuisine=None):
    use_postgis = database.has_postgis()
    sql = restaurants_within_sql(use_postgis, cuisine)
    params = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "radius": float(radius_km), "cuisine": cuisine}
    frame, elapsed = database.run_query(sql, params)
    return frame, database.render(sql, params), elapsed


def nearest_partners_sql(use_postgis):
    if use_postgis:
        return """
SELECT partner_id, name, vehicle, rating, latitude, longitude,
       ROUND((ST_Distance(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) / 1000)::numeric, 2) AS distance_km
FROM delivery_partner
WHERE is_available = TRUE
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
LIMIT %(limit)s;"""
    return """
SELECT partner_id, name, vehicle, rating, latitude, longitude,
       ROUND(distance_km(%(lat)s, %(lon)s, latitude, longitude)::numeric, 2) AS distance_km
FROM delivery_partner
WHERE is_available = TRUE
ORDER BY distance_km(%(lat)s, %(lon)s, latitude, longitude)
LIMIT %(limit)s;"""


def nearest_partners(lat, lon, limit=5):
    use_postgis = database.has_postgis()
    sql = nearest_partners_sql(use_postgis)
    params = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "limit": int(limit)}
    frame, elapsed = database.run_query(sql, params)
    return frame, database.render(sql, params), elapsed


def nearest_restaurants_sql(use_postgis):
    if use_postgis:
        return """
SELECT restaurant_id, name, cuisine, locality, rating, latitude, longitude,
       ROUND((ST_Distance(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) / 1000)::numeric, 2) AS distance_km
FROM restaurant
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
LIMIT %(limit)s;"""
    return """
SELECT restaurant_id, name, cuisine, locality, rating, latitude, longitude,
       ROUND(distance_km(%(lat)s, %(lon)s, latitude, longitude)::numeric, 2) AS distance_km
FROM restaurant
ORDER BY distance_km(%(lat)s, %(lon)s, latitude, longitude)
LIMIT %(limit)s;"""


def nearest_restaurants(lat, lon, limit=5):
    use_postgis = database.has_postgis()
    sql = nearest_restaurants_sql(use_postgis)
    params = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "limit": int(limit)}
    frame, elapsed = database.run_query(sql, params)
    return frame, database.render(sql, params), elapsed


def coverage_by_locality(radius_km):
    sql = """
SELECT c.locality,
       COUNT(DISTINCT c.customer_id) AS customers,
       ROUND(AVG(nearby.restaurants), 1) AS avg_restaurants_in_reach
FROM customer c
CROSS JOIN LATERAL (
    SELECT COUNT(*) AS restaurants
    FROM restaurant r
    WHERE distance_km(c.latitude, c.longitude, r.latitude, r.longitude) <= %(radius)s
) nearby
GROUP BY c.locality
ORDER BY avg_restaurants_in_reach;"""
    frame, elapsed = database.run_query(sql, {"radius": float(radius_km)})
    return frame, database.render(sql, {"radius": float(radius_km)}), elapsed


def delivery_points(limit=6000):
    sql = """
SELECT c.latitude, c.longitude, o.total_amount
FROM orders o
JOIN customer c ON c.customer_id = o.customer_id
WHERE o.status = 'DELIVERED'
ORDER BY o.order_time DESC
LIMIT %s;"""
    return database.fetch(sql, (int(limit),))


def all_restaurants():
    return database.fetch("SELECT restaurant_id, name, cuisine, locality, rating, latitude, longitude FROM restaurant ORDER BY name")


def all_partners():
    return database.fetch("SELECT partner_id, name, vehicle, is_available, latitude, longitude FROM delivery_partner")
