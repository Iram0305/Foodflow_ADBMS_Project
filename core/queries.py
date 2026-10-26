QUERIES = [
    {
        "title": "Most popular restaurants",
        "category": "Aggregation",
        "concept": "GROUP BY, COUNT, JOIN, LIMIT",
        "question": "Which restaurants receive the most orders?",
        "chart": ("bar", "restaurant", "total_orders"),
        "sql": """SELECT r.name AS restaurant, r.cuisine, r.locality,
       COUNT(o.order_id) AS total_orders
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
GROUP BY r.restaurant_id, r.name, r.cuisine, r.locality
ORDER BY total_orders DESC
LIMIT 10;""",
    },
    {
        "title": "Revenue by cuisine",
        "category": "Aggregation",
        "concept": "SUM, AVG, FILTER clause",
        "question": "How much delivered revenue does each cuisine bring in?",
        "chart": ("bar", "cuisine", "revenue"),
        "sql": """SELECT r.cuisine,
       COUNT(*) AS orders,
       SUM(o.total_amount) FILTER (WHERE o.status = 'DELIVERED') AS revenue,
       ROUND(AVG(o.total_amount), 2) AS avg_order_value
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
GROUP BY r.cuisine
ORDER BY revenue DESC;""",
    },
    {
        "title": "Full order details (5-table join)",
        "category": "Complex JOIN",
        "concept": "INNER JOIN, LEFT JOIN across 5 tables",
        "question": "Show the latest orders with customer, restaurant, payment and delivery partner.",
        "chart": None,
        "sql": """SELECT o.order_id, c.name AS customer, r.name AS restaurant,
       o.total_amount, p.method, p.status AS payment_status,
       dp.name AS delivery_partner, d.distance_km, o.status
FROM orders o
JOIN customer c ON c.customer_id = o.customer_id
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
JOIN payment p ON p.order_id = o.order_id
LEFT JOIN delivery d ON d.order_id = o.order_id
LEFT JOIN delivery_partner dp ON dp.partner_id = d.partner_id
ORDER BY o.order_time DESC
LIMIT 20;""",
    },
    {
        "title": "Restaurants above the overall average order value",
        "category": "Subquery",
        "concept": "Correlated aggregation + HAVING with scalar subquery",
        "question": "Which restaurants have an average order value higher than the platform average?",
        "chart": ("bar", "restaurant", "avg_order_value"),
        "sql": """SELECT r.name AS restaurant, r.cuisine,
       ROUND(AVG(o.total_amount), 2) AS avg_order_value,
       (SELECT ROUND(AVG(total_amount), 2) FROM orders) AS platform_average
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
GROUP BY r.restaurant_id, r.name, r.cuisine
HAVING AVG(o.total_amount) > (SELECT AVG(total_amount) FROM orders)
ORDER BY avg_order_value DESC
LIMIT 15;""",
    },
    {
        "title": "Rank restaurants inside each cuisine",
        "category": "Window function",
        "concept": "RANK() OVER (PARTITION BY ... ORDER BY ...)",
        "question": "Who is the top earner in every cuisine?",
        "chart": None,
        "sql": """SELECT cuisine, restaurant, revenue, rank_in_cuisine
FROM (
    SELECT r.cuisine, r.name AS restaurant,
           SUM(o.total_amount) AS revenue,
           RANK() OVER (PARTITION BY r.cuisine ORDER BY SUM(o.total_amount) DESC) AS rank_in_cuisine
    FROM orders o
    JOIN restaurant r ON r.restaurant_id = o.restaurant_id
    WHERE o.status = 'DELIVERED'
    GROUP BY r.cuisine, r.restaurant_id, r.name
) ranked
WHERE rank_in_cuisine <= 3
ORDER BY cuisine, rank_in_cuisine;""",
    },
    {
        "title": "Daily revenue with 7-day moving average",
        "category": "Window function",
        "concept": "AVG() OVER (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)",
        "question": "How is revenue trending once daily noise is smoothed out?",
        "chart": ("line", "day", ["revenue", "moving_avg_7d"]),
        "sql": """SELECT day, revenue,
       ROUND(AVG(revenue) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS moving_avg_7d,
       SUM(revenue) OVER (ORDER BY day) AS running_total
FROM (
    SELECT DATE(order_time) AS day, SUM(total_amount) AS revenue
    FROM orders
    WHERE status = 'DELIVERED'
    GROUP BY DATE(order_time)
) daily
ORDER BY day;""",
    },
    {
        "title": "Month-over-month growth",
        "category": "Window function",
        "concept": "LAG() to compare with the previous row",
        "question": "By how much did orders and revenue grow each month?",
        "chart": ("bar", "month", "growth_percent"),
        "sql": """SELECT TO_CHAR(month, 'Mon YYYY') AS month, orders, revenue,
       ROUND((revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month) * 100, 1) AS growth_percent
FROM (
    SELECT DATE_TRUNC('month', order_time) AS month,
           COUNT(*) AS orders,
           SUM(total_amount) AS revenue
    FROM orders
    WHERE status = 'DELIVERED'
    GROUP BY 1
) monthly
ORDER BY monthly.month;""",
    },
    {
        "title": "Average delivery time by restaurant",
        "category": "Temporal",
        "concept": "Interval arithmetic on timestamps, EXTRACT(EPOCH)",
        "question": "Which restaurants deliver the fastest from order to doorstep?",
        "chart": ("bar", "restaurant", "avg_minutes"),
        "sql": """SELECT r.name AS restaurant, r.cuisine,
       COUNT(*) AS deliveries,
       ROUND(AVG(EXTRACT(EPOCH FROM (d.delivered_time - o.order_time)) / 60)::numeric, 1) AS avg_minutes
FROM orders o
JOIN delivery d ON d.order_id = o.order_id
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
WHERE d.delivered_time IS NOT NULL
GROUP BY r.restaurant_id, r.name, r.cuisine
HAVING COUNT(*) >= 20
ORDER BY avg_minutes
LIMIT 15;""",
    },
    {
        "title": "Peak ordering hours",
        "category": "Temporal",
        "concept": "EXTRACT(HOUR), CASE buckets",
        "question": "When during the day do customers order the most?",
        "chart": ("bar", "hour", "orders"),
        "sql": """SELECT EXTRACT(HOUR FROM order_time)::int AS hour,
       CASE
           WHEN EXTRACT(HOUR FROM order_time) BETWEEN 6 AND 11 THEN 'Breakfast'
           WHEN EXTRACT(HOUR FROM order_time) BETWEEN 12 AND 15 THEN 'Lunch'
           WHEN EXTRACT(HOUR FROM order_time) BETWEEN 16 AND 18 THEN 'Snacks'
           WHEN EXTRACT(HOUR FROM order_time) BETWEEN 19 AND 23 THEN 'Dinner'
           ELSE 'Late night'
       END AS meal_slot,
       COUNT(*) AS orders
FROM orders
GROUP BY 1, 2
ORDER BY hour;""",
    },
    {
        "title": "Restaurants within 3 km of a customer",
        "category": "Spatial",
        "concept": "Haversine distance_km() / PostGIS ST_DWithin",
        "question": "Which restaurants can deliver to customer 101 within 3 km?",
        "chart": ("bar", "restaurant", "distance_km"),
        "sql": """SELECT r.name AS restaurant, r.cuisine, r.rating,
       ROUND(distance_km(c.latitude, c.longitude, r.latitude, r.longitude)::numeric, 2) AS distance_km
FROM customer c
CROSS JOIN restaurant r
WHERE c.customer_id = 101
  AND distance_km(c.latitude, c.longitude, r.latitude, r.longitude) <= 3
ORDER BY distance_km;""",
    },
    {
        "title": "Loyal customers (CTE)",
        "category": "CTE",
        "concept": "WITH clause, NTILE window, multi-step logic",
        "question": "Who are the top spenders and which segment do they fall in?",
        "chart": None,
        "sql": """WITH spend AS (
    SELECT customer_id, COUNT(*) AS orders, SUM(total_amount) AS lifetime_value,
           MAX(order_time) AS last_order
    FROM orders
    WHERE status = 'DELIVERED'
    GROUP BY customer_id
),
segmented AS (
    SELECT *, NTILE(4) OVER (ORDER BY lifetime_value DESC) AS quartile
    FROM spend
)
SELECT c.name, c.locality, s.orders, s.lifetime_value, s.last_order,
       CASE s.quartile WHEN 1 THEN 'Gold' WHEN 2 THEN 'Silver' WHEN 3 THEN 'Bronze' ELSE 'New' END AS segment
FROM segmented s
JOIN customer c ON c.customer_id = s.customer_id
ORDER BY s.lifetime_value DESC
LIMIT 15;""",
    },
    {
        "title": "Payment failure rate by method",
        "category": "Aggregation",
        "concept": "Conditional aggregation with FILTER",
        "question": "Which payment methods fail or get refunded most often?",
        "chart": ("bar", "method", "failure_percent"),
        "sql": """SELECT method,
       COUNT(*) AS payments,
       COUNT(*) FILTER (WHERE status = 'FAILED') AS failed,
       COUNT(*) FILTER (WHERE status = 'REFUNDED') AS refunded,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'FAILED') / COUNT(*), 2) AS failure_percent
FROM payment
GROUP BY method
ORDER BY failure_percent DESC;""",
    },
    {
        "title": "Customers who order but never review",
        "category": "Subquery",
        "concept": "NOT EXISTS anti-join",
        "question": "Which frequent customers have never written a single review?",
        "chart": None,
        "sql": """SELECT c.name, c.locality, COUNT(o.order_id) AS delivered_orders
FROM customer c
JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'DELIVERED'
WHERE NOT EXISTS (
    SELECT 1 FROM review rv WHERE rv.customer_id = c.customer_id
)
GROUP BY c.customer_id, c.name, c.locality
ORDER BY delivered_orders DESC
LIMIT 15;""",
    },
    {
        "title": "Revenue by locality and cuisine with subtotals",
        "category": "OLAP",
        "concept": "GROUP BY ROLLUP, GROUPING()",
        "question": "Revenue per locality broken down by cuisine, with locality subtotals.",
        "chart": None,
        "sql": """SELECT CASE WHEN GROUPING(r.locality) = 1 THEN 'ALL LOCALITIES' ELSE r.locality END AS locality,
       CASE WHEN GROUPING(r.cuisine) = 1 THEN 'Subtotal' ELSE r.cuisine END AS cuisine,
       SUM(o.total_amount) AS revenue,
       COUNT(*) AS orders
FROM orders o
JOIN restaurant r ON r.restaurant_id = o.restaurant_id
WHERE o.status = 'DELIVERED'
GROUP BY ROLLUP (r.locality, r.cuisine)
ORDER BY GROUPING(r.locality), r.locality, GROUPING(r.cuisine), revenue DESC
LIMIT 40;""",
    },
    {
        "title": "Delivery partner leaderboard",
        "category": "Complex JOIN",
        "concept": "JOIN + aggregates + DENSE_RANK",
        "question": "Which partners delivered the most and fastest?",
        "chart": ("bar", "partner", "deliveries"),
        "sql": """SELECT dp.name AS partner, dp.vehicle,
       COUNT(*) AS deliveries,
       ROUND(SUM(d.distance_km), 1) AS total_km,
       ROUND(AVG(EXTRACT(EPOCH FROM (d.delivered_time - d.pickup_time)) / 60)::numeric, 1) AS avg_ride_minutes,
       DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS position
FROM delivery d
JOIN delivery_partner dp ON dp.partner_id = d.partner_id
WHERE d.delivered_time IS NOT NULL
GROUP BY dp.partner_id, dp.name, dp.vehicle
ORDER BY deliveries DESC
LIMIT 10;""",
    },
    {
        "title": "Restaurant scorecard from the materialized view",
        "category": "Materialized view",
        "concept": "Pre-computed results with REFRESH MATERIALIZED VIEW",
        "question": "Instant dashboard numbers without recomputing joins every time.",
        "chart": None,
        "sql": """SELECT name, cuisine, locality, total_orders, revenue, avg_order_value, rating
FROM restaurant_stats
ORDER BY revenue DESC
LIMIT 15;""",
    },
]


def categories():
    names = []
    for query in QUERIES:
        if query["category"] not in names:
            names.append(query["category"])
    return names
